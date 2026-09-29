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


def run_sql(sql, output=False):
    # Ejecuta una consulta y devuelve su resultado si se solicita.
    result = subprocess.run(
        PSQL + ["-Atc" if output else "-c", sql],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=output,
    )
    return result.stdout.strip() if output else ""


def main():
    # Busca tablas como data_2022_oct, data_2023_jan, etc.
    query = """
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
          AND tablename ~ '^data_202[0-9]_[a-z]{3}$'
        ORDER BY tablename;
    """
    tables = run_sql(query, output=True).splitlines()

    if not tables:
        raise RuntimeError("No se encontraron tablas data_202*_***")

    # Junta todas las tablas sin eliminar filas repetidas.
    union = " UNION ALL ".join(f'SELECT * FROM "{table}"' for table in tables)

    # Borra customers si ya existe y la crea de nuevo.
    run_sql(f'DROP TABLE IF EXISTS customers; CREATE TABLE customers AS {union};')

    # Muestra el resultado final.
    rows = run_sql("SELECT COUNT(*) FROM customers;", output=True)
    print(f"customers creada con {rows} filas")


if __name__ == "__main__":
    main()
