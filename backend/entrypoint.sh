#!/bin/sh
# Starts as root only long enough to make the data volume writable, then runs the
# app as the unprivileged "app" user. Hosts such as Pxxl mount volumes as root,
# which would otherwise make SQLite fail with "unable to open database file".
set -e

if [ "$(id -u)" = "0" ]; then
  mkdir -p "$(dirname "${DATABASE_PATH:-/data/clinic.db}")"
  chown -R app:app "$(dirname "${DATABASE_PATH:-/data/clinic.db}")" 2>/dev/null \
    || echo "entrypoint: could not chown the data directory" >&2

  if setpriv --reuid=app --regid=app --init-groups true 2>/dev/null; then
    exec setpriv --reuid=app --regid=app --init-groups "$@"
  fi
  echo "entrypoint: cannot drop privileges here, running as root" >&2
fi

exec "$@"
