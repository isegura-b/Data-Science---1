FROM debian:bookworm

# pgAdmin se instala en un entorno virtual mínimo.
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-venv ca-certificates libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m venv /opt/pgadmin \
    && /opt/pgadmin/bin/pip install --no-cache-dir pgadmin4==9.8 gunicorn \
    && useradd -r -m -d /var/lib/pgadmin pgadmin \
    && mkdir -p /etc/pgadmin \
    && chown -R pgadmin:pgadmin /var/lib/pgadmin

COPY config_system.py servers.json /etc/pgadmin/
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

USER pgadmin
EXPOSE 5050
ENTRYPOINT ["docker-entrypoint.sh"]
