#!/bin/bash
set -eu

# Prepara el volumen como root y continúa con el usuario de PostgreSQL.
if [ "$(id -u)" = 0 ]; then
    chown -R postgres:postgres "$PGDATA" /var/run/postgresql
    chmod 700 "$PGDATA"
    exec setpriv --reuid=postgres --regid=postgres --init-groups "$0" "$@"
fi

: "${POSTGRES_USER:?POSTGRES_USER no está definido}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD no está definido}"
: "${POSTGRES_DB:?POSTGRES_DB no está definido}"

# Inicializa la base de datos solamente cuando el volumen está vacío.
if [ ! -s "$PGDATA/PG_VERSION" ]; then
    initdb -D "$PGDATA" --username=postgres --encoding=UTF8 \
        --auth-local=trust --auth-host=scram-sha-256

    echo "listen_addresses = '*'" >> "$PGDATA/postgresql.conf"
    echo "host all all 0.0.0.0/0 scram-sha-256" >> "$PGDATA/pg_hba.conf"
    echo "host all all ::/0 scram-sha-256" >> "$PGDATA/pg_hba.conf"

    pg_ctl -D "$PGDATA" -o "-c listen_addresses=''" -w start
    psql -v ON_ERROR_STOP=1 -U postgres \
        --set=user="$POSTGRES_USER" \
        --set=password="$POSTGRES_PASSWORD" \
        --set=database="$POSTGRES_DB" <<'SQL'
CREATE USER :"user" WITH SUPERUSER PASSWORD :'password';
CREATE DATABASE :"database" OWNER :"user";
SQL
    pg_ctl -D "$PGDATA" -m fast -w stop
fi

# PostgreSQL queda en primer plano como PID 1.
exec postgres -D "$PGDATA"
