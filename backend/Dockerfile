FROM python:3.13.15-slim-bookworm@sha256:2325bb286ec344af3e5898cc224b5844e2707ac6e26b1632516fd3edc84a5e26

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY backend/requirements.txt /tmp/requirements.txt
RUN python -m pip install --no-cache-dir -r /tmp/requirements.txt

ARG APP_UID=1000
ARG APP_GID=1000
RUN groupadd --gid ${APP_GID} app \
    && useradd --uid ${APP_UID} --gid app --create-home app \
    && mkdir -p /app/staticfiles /app/media \
    && chown -R app:app /app

COPY --chown=app:app backend/ /app/
COPY backend/entrypoint.sh /usr/local/bin/herbal-store-entrypoint
RUN chmod 755 /usr/local/bin/herbal-store-entrypoint

USER app

EXPOSE 8000
ENTRYPOINT ["herbal-store-entrypoint"]
CMD ["gunicorn", "config.wsgi:application", "--bind=0.0.0.0:8000", "--workers=2"]
