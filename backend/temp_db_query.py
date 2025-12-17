import psycopg2


def main() -> None:
    conn = psycopg2.connect(
        "postgresql://content_jumprsart_db_user:r4AdMU6F37DmlGSMhYWnu4fv5EDJNK2G@dpg-d4uunmvpm1nc73bdling-a.oregon-postgres.render.com/content_jumprsart_db"
    )
    cur = conn.cursor()
    cur.execute("SELECT version();")
    print(f"PostgreSQL version: {cur.fetchone()[0]}\n")

    cur.execute(
        """
        SELECT table_schema, table_name
        FROM information_schema.tables
        WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
        ORDER BY table_schema, table_name;
        """
    )
    tables = cur.fetchall()
    print("Tables:")
    for schema, table in tables:
        print(f"{schema}.{table}")

    print("\nColumns:")
    for schema, table in tables:
        cur.execute(
            """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema=%s AND table_name=%s
            ORDER BY ordinal_position;
            """,
            (schema, table),
        )
        cols = cur.fetchall()
        print(f"\n{schema}.{table}")
        for name, dtype, nullable, default in cols:
            print(f"  {name}: {dtype}, nullable={nullable}, default={default}")

    cur.execute(
        """
        SELECT schemaname, tablename
        FROM pg_catalog.pg_tables
        ORDER BY schemaname, tablename;
        """
    )
    pg_tables = cur.fetchall()
    print("\nAll pg_tables:")
    for schema, table in pg_tables:
        print(f"{schema}.{table}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
