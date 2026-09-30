#!/usr/bin/env python3

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path


# Carpeta donde está este script. Así las rutas funcionan aunque lo ejecutes
# desde otro directorio.
ROOT = Path(__file__).resolve().parent


# Columnas y tipos que tendrán las tablas creadas desde los CSV de customer.
CUSTOMER_SCHEMA = """
    event_time TIMESTAMPTZ,
    event_type TEXT,
    product_id BIGINT,
    price NUMERIC,
    user_id BIGINT,
    user_session UUID
"""

# Columnas y tipos de la tabla item.
ITEM_SCHEMA = """
    product_id BIGINT,
    category_id BIGINT,
    category_code TEXT,
    brand TEXT
"""


# Parte común de todos los comandos que ejecutan psql dentro del contenedor db.
# -T evita reservar una terminal: es necesario para enviarle el CSV por stdin.
# El usuario y la base se leen de las variables de entorno del contenedor.
PSQL = [
    "docker", "compose", "exec", "-T", "db", "sh", "-c",
    'exec psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" '
    '-d "$POSTGRES_DB" "$@"',
    "sh",
]

#Ejecuta una instrucción SQL en PostgreSQL.
def psql(sql):
    subprocess.run(
        PSQL + ["-c", sql],
        cwd=ROOT,
        check=True,  # Si psql falla, Python detiene el programa
    )


def load_csv(path, schema):
    # Si no existe el CSV, avisa y continúa sin crear ni borrar la tabla.
    if not path.is_file():
        print(f"No se encuentra el archivo: {path}", flush=True)
        return

    # Crea una tabla a partir del nombre del CSV e importa sus filas.
    table = path.stem

    # El nombre de tabla se insertará en una consulta SQL.
    # Por eso solo aceptamos letras, números y guiones bajos.
    if not re.fullmatch(r"[a-zA-Z_][a-zA-Z_0-9]*", table):
        raise ValueError(f"Nombre de tabla no válido: {table}")

    # Borra la versión anterior para reflejar cualquier cambio del CSV.
    psql(f'DROP TABLE IF EXISTS "{table}"')

    # Crea de nuevo la tabla con el esquema correspondiente.
    psql(f'CREATE TABLE "{table}" ({schema})')

    print(f'{table}: recreando desde {path.name}...', flush=True)

    # Abre el CSV en el ordenador y envía su contenido a psql.
    # \copy interpreta la primera línea como cabecera (HEADER TRUE).
    with path.open("rb") as csv_file:
        subprocess.run(
            PSQL + [ "-c", f'\\copy "{table}" FROM STDIN WITH (FORMAT CSV, HEADER TRUE)', ],
            cwd=ROOT,
            stdin=csv_file,
            check=True,
        )


def start_project():
    """Arranca Docker y carga los CSV en PostgreSQL."""
    # Construye las imágenes necesarias y arranca los contenedores en segundo plano.
    subprocess.run(
        ["docker", "compose", "up", "--build", "-d"],
        cwd=ROOT,
        check=True,
    )

    # PostgreSQL puede tardar unos segundos en aceptar conexiones.
    # Probamos cada 2 segundos, hasta un máximo de 60 intentos.
    for _ in range(60):
        ready = subprocess.run(
            [
                "docker", "compose", "exec", "-T", "db", "sh", "-c",
                'pg_isready -q -U "$POSTGRES_USER" -d "$POSTGRES_DB"',
            ],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        if ready.returncode == 0:
            break

        time.sleep(2)
    else:
        # Este else pertenece al for: se ejecuta si nunca llegamos al break.
        raise RuntimeError("PostgreSQL no está disponible")

    # Crea e importa la tabla item.
    load_csv(ROOT / "subject/item/item.csv", ITEM_SCHEMA)

    # Crea e importa una tabla por cada CSV de subject/customer/.
    for path in sorted((ROOT / "subject/customer").glob("*.csv")):
        load_csv(path, CUSTOMER_SCHEMA)

    print("pgAdmin: http://127.0.0.1:5050")


def start_pgadmin():
    """Prepara la conexión automática que aparecerá en pgAdmin."""
    # Los valores de POSTGRES_DB y POSTGRES_USER llegan desde Docker Compose.
    server = {
        "Servers": {
            "1": {
                "Name": "Data Warehouse",
                "Group": "Servers",
                "Host": "db",
                "Port": 5432, 
                "MaintenanceDB": os.environ["POSTGRES_DB"],
                "Username": os.environ["POSTGRES_USER"],
                "SSLMode": "prefer",
            }
        }
    }

    # pgAdmin leerá este archivo para registrar el servidor.
    output = Path("/tmp/servers.json")
    output.write_text(json.dumps(server), encoding="utf-8")
    output.chmod(0o444)  # Permite que el usuario de pgAdmin lo lea

    # Sustituye este proceso por el arranque oficial de pgAdmin.
    os.execv("/entrypoint.sh", ["/entrypoint.sh"])

# Tú ejecutas «python3 start.py»: arranca Docker e importa los CSV.
# Docker ejecuta «start.py --pgadmin» dentro del contenedor pgAdmin:
# genera servers.json y después arranca pgAdmin.
if __name__ == "__main__":
    if sys.argv[1:] == ["--pgadmin"]:
        start_pgadmin()
    else:
        start_project()
