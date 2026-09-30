#!/usr/bin/env python3

import subprocess
import sys
import uuid
from pathlib import Path


# El compose debe estar en la raiz, y este archivo en ex03/.
ROOT = Path(__file__).resolve().parent.parent
PSQL = [
    "docker", "compose", "exec", "-T", "db", "sh", "-c",
    'PGCONNECT_TIMEOUT=5 exec psql -X -v ON_ERROR_STOP=1 '
    '-U "$POSTGRES_USER" -d "$POSTGRES_DB"',
]


def main():
    # Un nombre propio evita conflictos con tablas de intentos anteriores.
    new_table = "customers_fusion_" + uuid.uuid4().hex

    sql = rf"""
\echo 1/5: Conectado. Comprobando tablas y bloqueos...
BEGIN;
SET LOCAL lock_timeout = '3s';
SET LOCAL statement_timeout = '10min';
SET LOCAL work_mem = '128MB';

-- Comprueba que customers exista antes de intentar bloquearla.
DO $$
BEGIN
    IF to_regclass('public.customers') IS NULL THEN
        RAISE EXCEPTION 'customers no existe. Ejecuta primero el ex01.';
    END IF;
END $$;

-- NOWAIT da un error inmediato si otra conexion bloquea las tablas.
LOCK TABLE public.customers IN ACCESS EXCLUSIVE MODE NOWAIT;

-- Comprueba que tenga eventos sin contar millones de filas.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM public.customers LIMIT 1) THEN
        RAISE EXCEPTION 'customers esta vacia. Ejecuta el ex01 y el ex02 antes de fusionar.';
    END IF;
END $$;

LOCK TABLE public.item IN SHARE MODE NOWAIT;

\echo 2/5: Preparando las fichas de productos...
-- Elimina solo fichas completamente identicas, no fichas distintas.
CREATE TEMP TABLE fusion_items ON COMMIT DROP AS
SELECT DISTINCT product_id, category_id, category_code, brand
FROM public.item;
CREATE INDEX ON fusion_items (product_id);
ANALYZE fusion_items;

\echo 3/5: Preparando las columnas de customers...
ALTER TABLE public.customers
    ADD COLUMN IF NOT EXISTS category_id BIGINT,
    ADD COLUMN IF NOT EXISTS category_code TEXT,
    ADD COLUMN IF NOT EXISTS brand TEXT;

\echo 4/5: Construyendo la fusion. Esta fase puede tardar...
CREATE TABLE public.{new_table} AS
SELECT
    c.event_time,
    c.event_type,
    c.product_id,
    c.price,
    c.user_id,
    c.user_session,
    COALESCE(i.category_id, c.category_id) AS category_id,
    COALESCE(i.category_code, c.category_code) AS category_code,
    COALESCE(i.brand, c.brand) AS brand
FROM public.customers AS c
LEFT JOIN fusion_items AS i ON c.product_id = i.product_id;

\echo 5/5: Sustituyendo customers y guardando...
-- Si hay dependencias, falla sin borrarlas: no se usa CASCADE.
DROP TABLE public.customers;
ALTER TABLE public.{new_table} RENAME TO customers;
COMMIT;
\echo Fusion guardada correctamente.
"""

    print("Iniciando fusion de customers con item...", flush=True)
    try:
        subprocess.run(PSQL, input=sql, text=True, cwd=ROOT, check=True)
    except (OSError, subprocess.CalledProcessError) as error:
        print(
            f"\nFusion fallida: {error}\n"
            "Si aparece un ERROR de SQL antes de COMMIT, se deshacen los cambios.\n"
            "Si dice 'could not obtain lock', otra conexion esta usando la tabla.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
