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
    # Compara todas las columnas salvo la fecha, incluidas las fichas de
    # producto si se vuelve a ejecutar la limpieza despues de la fusion.
    result = subprocess.run(
        PSQL + [
            "-tAc",
            """
            SELECT string_agg(quote_ident(attname), ', ' ORDER BY attnum)
            FROM pg_attribute
            WHERE attrelid = to_regclass('public.customers')
              AND attnum > 0 AND NOT attisdropped
              AND attname <> 'event_time';
            """,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    # Si no existe, avisa y termina sin ejecutar la limpieza.
    partition_columns = result.stdout.strip()
    if not partition_columns:
        print("No existe la tabla customers. Ejecuta primero el ejercicio 01.")
        return

    sql = f"""
        BEGIN;

        -- Si otra consulta bloquea la tabla, avisa tras 10 segundos.
        SET LOCAL lock_timeout = '10s';

        -- Memoria disponible para ordenar en esta conexión.
        SET LOCAL work_mem = '128MB';

        -- Evita cambios en customers mientras hacemos la limpieza.
        LOCK TABLE public.customers IN ACCESS EXCLUSIVE MODE;

        -- Guarda únicamente los eventos que queremos conservar.
        CREATE TEMP TABLE customers_clean ON COMMIT DROP AS
        SELECT (event_row).*
        FROM (
            SELECT
                c AS event_row,
                -- Se compara con el evento anterior original, incluso si
                -- ese evento se elimina: los intervalos <= 1 s se agrupan.
                event_time - LAG(event_time) OVER (
                    PARTITION BY {partition_columns}
                    ORDER BY event_time, ctid
                ) AS time_difference
            FROM public.customers AS c
        ) AS events
        WHERE time_difference IS NULL
           OR time_difference > INTERVAL '1 second';

        -- Muestra cuántas filas se van a eliminar.
        SELECT
            (SELECT COUNT(*) FROM public.customers)
            - (SELECT COUNT(*) FROM customers_clean)
            AS duplicates_removed;

        -- Vacía la tabla y recupera las filas válidas.
        TRUNCATE TABLE public.customers;

        -- Conserva también las columnas añadidas por la fusión.
        INSERT INTO public.customers SELECT * FROM customers_clean;

        COMMIT;

        ANALYZE public.customers;
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
