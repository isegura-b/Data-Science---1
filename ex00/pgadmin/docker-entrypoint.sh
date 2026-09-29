#!/bin/bash
set -eu

: "${PGADMIN_DEFAULT_EMAIL:?PGADMIN_DEFAULT_EMAIL no está definido}"
: "${PGADMIN_DEFAULT_PASSWORD:?PGADMIN_DEFAULT_PASSWORD no está definido}"
: "${POSTGRES_USER:?POSTGRES_USER no está definido}"

PGADMIN_DIR=$(/opt/pgadmin/bin/python -c \
    'import importlib.util; print(next(iter(importlib.util.find_spec("pgadmin4").submodule_search_locations)))')

# Crea el usuario de pgAdmin y registra PostgreSQL la primera vez.
if [ ! -f /var/lib/pgadmin/pgadmin4.db ]; then
    export PGADMIN_SETUP_EMAIL="$PGADMIN_DEFAULT_EMAIL"
    export PGADMIN_SETUP_PASSWORD="$PGADMIN_DEFAULT_PASSWORD"
    /opt/pgadmin/bin/python "$PGADMIN_DIR/setup.py" setup-db

    sed "s/__POSTGRES_USER__/$POSTGRES_USER/" /etc/pgadmin/servers.json > /tmp/servers.json
    /opt/pgadmin/bin/python "$PGADMIN_DIR/setup.py" load-servers /tmp/servers.json \
        --user "$PGADMIN_DEFAULT_EMAIL"
    rm -f /tmp/servers.json
fi

# Gunicorn queda en primer plano como PID 1.
exec /opt/pgadmin/bin/gunicorn --bind 0.0.0.0:5050 --workers 1 --threads 25 \
    --chdir "$PGADMIN_DIR" pgAdmin4:app
