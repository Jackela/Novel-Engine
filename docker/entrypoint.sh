#!/bin/sh
# Container entrypoint: guarantee a usable session secret before the server
# starts. When SECURITY_SECRET_KEY is unset or empty, the value is read from
# (or generated into) /app/data/.secret inside the persistent volume, so a
# fresh volume needs no manual secret and sessions survive container
# replacement. The secret value is never echoed or logged; any read, write,
# or generation failure aborts startup loudly instead of silently rotating
# sessions on every restart.
set -eu

SECRET_FILE=/app/data/.secret

if [ -z "${SECURITY_SECRET_KEY:-}" ]; then
  if [ -f "$SECRET_FILE" ]; then
    # Tolerate a trailing newline or CR from hand-edited files, but refuse an
    # empty result: starting without a usable secret would invalidate every
    # session on the next restart.
    SECRET_VALUE=$(tr -d '\r\n' < "$SECRET_FILE")
    if [ -z "$SECRET_VALUE" ]; then
      echo "entrypoint: $SECRET_FILE is empty; remove it or set SECURITY_SECRET_KEY" >&2
      exit 1
    fi
  else
    SECRET_VALUE=$(node -e "process.stdout.write(require('node:crypto').randomBytes(32).toString('hex'))")
    # 177 (umask) makes the very first write create the file 0600; scoping it
    # to a subshell keeps the server process's umask untouched. The explicit
    # chmod is defense in depth for exotic filesystems that ignore umask.
    (umask 177 && printf '%s\n' "$SECRET_VALUE" > "$SECRET_FILE")
    chmod 600 "$SECRET_FILE"
  fi
  export SECURITY_SECRET_KEY="$SECRET_VALUE"
fi

exec "$@"
