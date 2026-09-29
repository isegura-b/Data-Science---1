#!/usr/bin/env python3

import subprocess
from pathlib import Path


# Raiz del proyecto, donde esta docker-compose.yml.
ROOT = Path(__file__).resolve().parent.parent

# Comando para ejecutar SQL en PostgreSQL dentro de Docker.
PSQL = [
    "docker", "compose", "exec", "-T", "db", "sh", "-c",
    'exec psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" '
    '-d "$POSTGRES_DB" "$@"',
    "sh",
]


def main():
    sql = """
        -- Anade a customers las columnas que contiene item.
        ALTER TABLE customers
            ADD COLUMN IF NOT EXISTS category_id BIGINT,
            ADD COLUMN IF NOT EXISTS category_code TEXT,
            ADD COLUMN IF NOT EXISTS brand TEXT;

        -- Une ambas tablas por product_id sin borrar ningun cliente.
        UPDATE customers AS customers
        SET category_id = item.category_id,
            category_code = item.category_code,
            brand = item.brand
        FROM item AS item
        WHERE customers.product_id = item.product_id;
    """

    # Ejecuta la fusion dentro de PostgreSQL.
    subprocess.run(
        PSQL + ["-c", sql],
        cwd=ROOT,
        check=True,
    )


if __name__ == "__main__":
    main()
