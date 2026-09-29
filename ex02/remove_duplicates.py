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
    # LAG compara cada evento con el evento igual que ocurrio antes.
    # Si sucedieron con 0 o 1 segundo de diferencia, elimina el mas reciente.
    sql = """
        DELETE FROM customers
        WHERE ctid IN (
            SELECT row_id
            FROM (
                SELECT
                    ctid AS row_id,
                    event_time - LAG(event_time) OVER (
                        PARTITION BY event_type, product_id, price,
                                     user_id, user_session
                        ORDER BY event_time, ctid
                    ) AS time_difference
                FROM customers
            ) AS events
            WHERE time_difference <= INTERVAL '1 second'
        );
    """

    # Ejecuta la eliminacion y muestra cuantas filas fueron borradas.
    subprocess.run(
        PSQL + ["-c", sql],
        cwd=ROOT,
        check=True,
    )


if __name__ == "__main__":
    main()
