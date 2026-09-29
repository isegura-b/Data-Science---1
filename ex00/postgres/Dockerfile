FROM debian:bookworm

# Instalamos PostgreSQL sin crear el clúster automático de Debian.
RUN mkdir -p /etc/postgresql-common \
    && echo "create_main_cluster = false" > /etc/postgresql-common/createcluster.conf \
    && apt-get update \
    && apt-get install -y --no-install-recommends postgresql-15 \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/usr/lib/postgresql/15/bin:$PATH" \
    PGDATA=/var/lib/postgresql/data

RUN mkdir -p "$PGDATA" /var/run/postgresql \
    && chown -R postgres:postgres /var/lib/postgresql /var/run/postgresql \
    && chmod 700 "$PGDATA"

COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 5432
STOPSIGNAL SIGINT
ENTRYPOINT ["docker-entrypoint.sh"]
