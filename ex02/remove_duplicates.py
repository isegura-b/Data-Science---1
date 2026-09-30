#!/usr/bin/env python3

import subprocess
from pathlib import Path


# Raíz del proyecto, donde está docker-compose.yml.
ROOT = Path(__file__).resolve().parent.parent

# Ejecuta PostgreSQL dentro del contenedor.
PSQL = [
    "docker", "compose", "exec", "-T", "db", "sh", "-c",
    'exec psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" '
    '-d "$POSTGRES_DB" "$@"',
    "sh",
]


def main():
    # Comprueba si existe la tabla customers.
    result = subprocess.run(
        PSQL + [
            "-tAc",
            "SELECT to_regclass('public.customers') IS NOT NULL;",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    # Si no existe, avisa y termina sin ejecutar la limpieza.
    if result.stdout.strip() != "t":
        print("No existe la tabla customers. Ejecuta primero el ejercicio 01.")
        return

    sql = """
        BEGIN;

        -- Si otra consulta bloquea la tabla, avisa tras 10 segundos.
        SET LOCAL lock_timeout = '10s';

        -- Memoria disponible para ordenar en esta conexión.
        SET LOCAL work_mem = '128MB';

        -- Evita cambios en customers mientras hacemos la limpieza.
        LOCK TABLE customers IN ACCESS EXCLUSIVE MODE;

        -- Guarda únicamente los eventos que queremos conservar.
        CREATE TEMP TABLE customers_clean ON COMMIT DROP AS
        SELECT
            event_time,
            event_type,
            product_id,
            price,
            user_id,
            user_session
        FROM (
            SELECT
                *,
                event_time - LAG(event_time) OVER (
                    PARTITION BY event_type, product_id, price,
                                 user_id, user_session
                    ORDER BY event_time, ctid
                ) AS time_difference
            FROM customers
        ) AS events
        WHERE time_difference IS NULL
           OR time_difference > INTERVAL '1 second';

        -- Muestra cuántas filas se van a eliminar.
        SELECT
            (SELECT COUNT(*) FROM customers)
            - (SELECT COUNT(*) FROM customers_clean)
            AS duplicates_removed;

        -- Vacía la tabla y recupera las filas válidas.
        TRUNCATE TABLE customers;

        INSERT INTO customers (
            event_time, event_type, product_id,
            price, user_id, user_session
        )
        SELECT
            event_time, event_type, product_id,
            price, user_id, user_session
        FROM customers_clean;

        COMMIT;

        ANALYZE customers;
    """

    print("Limpiando customers; puede tardar con millones de filas...", flush=True)

    subprocess.run(
        PSQL + ["-c", sql],
        cwd=ROOT,
        check=True,
    )

    print("Limpieza terminada.", flush=True)


if __name__ == "__main__":
    main()