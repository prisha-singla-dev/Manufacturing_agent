import re
import uuid
from typing import Optional
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from backend.db import pool, BUSINESS_TABLES, WRITABLE_TABLES

# In-memory store for proposed writes awaiting user confirmation.
# Fine for a single-process dev/demo deployment; swap for Redis/DB if this
# ever runs multi-worker or needs to survive restarts.
PENDING_WRITES: dict[str, dict] = {}


def _insert_columns(sql: str) -> list[str] | None:
    m = re.search(r"insert\s+into\s+\w+\s*\(([^)]*)\)", sql, re.IGNORECASE)
    if not m:
        return None
    return [c.strip().strip('"').lower() for c in m.group(1).split(",")]


def _is_safe_select(sql: str) -> bool:
    s = sql.strip().rstrip(";").lower()
    if not s.startswith("select"):
        return False
    banned = ["insert", "update", "delete", "drop", "truncate", "alter", "grant", ";"]
    # allow at most the one statement (already stripped trailing ;), but
    # reject any of these keywords appearing anywhere (blocks chained/multi
    # statements and DML hidden in subqueries)
    return not any(word in s for word in banned)


@tool
def run_sql_read(query: str) -> str:
    """Run a read-only SELECT query against the manufacturing DB and return
    the results. Only SELECT statements are allowed. Always reference the
    real table/column names from the schema you were given. Results are
    capped at 200 rows — aggregate or filter in SQL rather than relying on
    LIMIT-less full scans."""
    if not _is_safe_select(query):
        return "ERROR: only single SELECT statements are allowed."
    try:
        with pool.connection() as conn:
            cur = conn.execute(query)
            rows = cur.fetchmany(200)
            if not rows:
                return "OK: query succeeded, 0 rows returned."
            cols = list(rows[0].keys())
            preview = [dict(r) for r in rows]
            return f"OK: {len(preview)} rows. columns={cols}\nrows={preview}"
    except Exception as e:
        return f"ERROR: {e}"


@tool
def propose_write(sql: str, explanation: str) -> str:
    """Propose a write (INSERT or UPDATE only) to the database. This does
    NOT execute the write — it stores the proposal and returns a
    proposal_id. The user must explicitly confirm via a separate step
    before it runs. Only use this for tables the user is clearly asking to
    modify (e.g. recording a new transaction or PO). Never propose
    DELETE/DROP/TRUNCATE."""
    s = sql.strip().rstrip(";").lower()
    if not (s.startswith("insert") or s.startswith("update")):
        return "ERROR: only INSERT or UPDATE may be proposed."
    if any(word in s for word in ["delete", "drop", "truncate", "alter", ";"]):
        return "ERROR: statement contains a disallowed keyword."
    if not any(t in s for t in WRITABLE_TABLES):
        return f"ERROR: target table must be one of {WRITABLE_TABLES}."

    if s.startswith("insert"):
        cols = _insert_columns(sql)
        if cols is not None and "id" not in cols:
            return (
                "ERROR: this table's `id` column has no database-side default "
                "(unlike `users`/`refresh_tokens`) — you must generate and "
                "include it explicitly. Retry the INSERT with `id` as the "
                "first column and `gen_random_uuid()::text` as its value."
            )

    proposal_id = str(uuid.uuid4())
    PENDING_WRITES[proposal_id] = {"sql": sql, "explanation": explanation}
    return f"PROPOSED: proposal_id={proposal_id}. Tell the user what will happen and that they must confirm it before it runs."


class ChartSpec(BaseModel):
    chart_type: str = Field(description="'bar' | 'line' | 'pie'")
    x_key: str
    y_key: str
    data: list[dict]


class RespondToUser(BaseModel):
    """Call this LAST, once you have everything you need, to deliver the
    final answer to the user. Always call this exactly once to end the turn
    — never end the turn without calling it."""
    response_type: str = Field(description="'text' | 'table' | 'chart' | 'confirm_write'")
    text: str = Field(description="Natural-language answer, always populated.")
    table: Optional[list[dict]] = Field(default=None, description="Rows for response_type='table'.")
    chart: Optional[ChartSpec] = Field(default=None, description="For response_type='chart'.")
    proposal_id: Optional[str] = Field(default=None, description="For response_type='confirm_write', the id from propose_write.")


ALL_TOOLS = [run_sql_read, propose_write]