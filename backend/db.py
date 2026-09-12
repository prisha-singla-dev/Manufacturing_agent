import os
from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))

DATABASE_URL = os.environ["DATABASE_URL"]

# Shared pool for regular queries AND the LangGraph checkpointer (see
# agent.py) — one pool, not two separate connections, so both benefit from
# the same health-checking instead of the checkpointer holding one raw
# connection open for the app's entire lifetime (which is what silently
# died against Railway's proxy after an idle period).
pool = ConnectionPool(
    DATABASE_URL,
    min_size=1,
    max_size=8,
    kwargs={"row_factory": dict_row},
    check=ConnectionPool.check_connection,
)

# Tables the agent is allowed to know about / query. Deliberately excludes
# LangGraph's internal persistence tables (checkpoint_*, alembic_version) and
# auth internals (refresh_tokens, password_hash) — those aren't business data.
BUSINESS_TABLES = [
    "inv_categories",
    "inv_current_stock",
    "inv_issued_to_targets",
    "inv_items",
    "inv_locations",
    "inv_sub_categories",
    "inv_sub_categories_2",
    "inv_transactions",
    "proc_po_line_regularisations",
    "proc_po_lines",
    "proc_po_payment_tranches",
    "proc_po_receipts",
    "proc_purchase_orders",
    "proc_unexpected_receipt_headers",
    "proc_unexpected_receipts",
    "proc_vendors",
]

# Tables the write tool is allowed to touch, and only via INSERT/UPDATE
# (never DELETE/DROP/TRUNCATE — enforced in tools.py regardless of this list).
WRITABLE_TABLES = [
    "inv_transactions",
    "proc_purchase_orders",
    "proc_po_lines",
    "proc_po_receipts",
]

_schema_cache: str | None = None


def get_schema_description() -> str:
    """Introspect BUSINESS_TABLES and return an LLM-friendly schema doc.
    Cached in-process since the schema doesn't change at runtime."""
    global _schema_cache
    if _schema_cache is not None:
        return _schema_cache

    lines = []
    with pool.connection() as conn:
        for table in BUSINESS_TABLES:
            cur = conn.execute(
                """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                ORDER BY ordinal_position
                """,
                (table,),
            )
            cols = cur.fetchall()
            col_desc = ", ".join(
                f"{c['column_name']} ({c['data_type']}{'*' if c['is_nullable'] == 'NO' else ''})"
                for c in cols
            )
            lines.append(f"- {table}: {col_desc}")

        cur = conn.execute(
            """
            SELECT tc.table_name, kcu.column_name, ccu.table_name AS foreign_table, ccu.column_name AS foreign_column
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name = ANY(%s)
            """,
            (BUSINESS_TABLES,),
        )
        fks = cur.fetchall()
        fk_lines = [
            f"- {fk['table_name']}.{fk['column_name']} -> {fk['foreign_table']}.{fk['foreign_column']}"
            for fk in fks
        ]

    _schema_cache = (
        "TABLES (* = NOT NULL):\n" + "\n".join(lines) +
        "\n\nFOREIGN KEYS:\n" + "\n".join(fk_lines)
    )
    return _schema_cache