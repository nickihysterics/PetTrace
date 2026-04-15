#!/bin/sh
set -eu

/entrypoint.sh "$@" &
pgadmin_pid=$!

trap 'kill -TERM "$pgadmin_pid" 2>/dev/null || true' INT TERM

python3 <<'PY'
import sqlite3
import time
from pathlib import Path

db_path = Path("/var/lib/pgadmin/pgadmin4.db")
deadline = time.time() + 120
command = "printenv POSTGRES_PASSWORD"

while time.time() < deadline:
    if not db_path.exists():
        time.sleep(1)
        continue

    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE server
               SET passexec_cmd = ?,
                   passexec_expiration = 0
             WHERE host = 'postgres'
               AND maintenance_db = 'pettrace'
               AND username = 'pettrace'
               AND COALESCE(passexec_cmd, '') = ''
            """,
            (command,),
        )
        conn.commit()
        updated = cur.rowcount
        conn.close()
        if updated:
            print(f"Configured pgAdmin password command for {updated} server(s).", flush=True)
            break
    except sqlite3.Error:
        pass

    time.sleep(1)
PY

wait "$pgadmin_pid"
