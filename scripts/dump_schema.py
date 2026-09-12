import psycopg2
import os

DATABASE_URL = os.environ["DATABASE_URL"]

def main():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """)
    tables = [r[0] for r in cur.fetchall()]
    print(f"Found {len(tables)} tables\n" + "=" * 40)

    for table in tables:
        print(f"\nTABLE: {table}")
        cur.execute("""
            SELECT id, email, full_name, role FROM users;
        """, (table,))
        for col, dtype, nullable, default in cur.fetchall():
            flag = "" if nullable == "YES" else " NOT NULL"
            defl = f" DEFAULT {default}" if default else ""
            print(f"  - {col}: {dtype}{flag}{defl}")

        # Foreign keys for this table
        cur.execute("""
            SELECT
                kcu.column_name,
                ccu.table_name AS foreign_table,
                ccu.column_name AS foreign_column
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage ccu
                ON tc.constraint_name = ccu.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name = %s;
        """, (table,))
        fks = cur.fetchall()
        if fks:
            print("  FKs:")
            for col, ftable, fcol in fks:
                print(f"    - {col} -> {ftable}.{fcol}")

        # Row count (cheap sanity check on fabricated vs real data)
        cur.execute(f'SELECT COUNT(*) FROM "{table}";')
        count = cur.fetchone()[0]
        print(f"  Row count: {count}")

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()