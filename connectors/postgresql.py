import csv
from typing import Any

from smart_ingestion.config import DATABASE_URL
from smart_ingestion.utils import sanitize_table_name


def get_connection_url(override: str | None) -> str:
    return override or DATABASE_URL


def load_csv_to_postgresql(
    csv_path: str,
    table_name: str,
    database_url: str | None = None,
) -> int:
    import psycopg

    table = sanitize_table_name(table_name)
    conn_url = get_connection_url(database_url)

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        if not rows:
            return 0
        columns = list(rows[0].keys())

    col_defs = ", ".join(f'"{c}" TEXT' for c in columns)
    placeholders = ", ".join("%s" for _ in columns)
    col_names = ", ".join(f'"{c}"' for c in columns)

    with psycopg.connect(conn_url) as conn:
        with conn.cursor() as cur:
            cur.execute(f'DROP TABLE IF EXISTS "{table}"')
            cur.execute(f'CREATE TABLE "{table}" ({col_defs})')
            insert_sql = f'INSERT INTO "{table}" ({col_names}) VALUES ({placeholders})'
            values: list[tuple[Any, ...]] = [
                tuple(row.get(c, "") for c in columns) for row in rows
            ]
            cur.executemany(insert_sql, values)
        conn.commit()

    return len(rows)
