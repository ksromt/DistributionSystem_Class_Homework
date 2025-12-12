import os
import psycopg2
import traceback

dsn = os.environ.get("DATABASE_URL")
print("DSN =", dsn)

def show_error(e: Exception):
    print("type:", type(e))
    print("error str:", str(e))
    print("error repr:", repr(e))
    print("pgerror:", getattr(e, "pgerror", None))
    print("pgcode :", getattr(e, "pgcode", None))
    print("args   :", getattr(e, "args", None))
    # psycopg2 OperationalError may carry diag info when server responds
    diag = getattr(e, "diag", None)
    if diag:
        print("diag:", diag)
        for attr in [
            "severity",
            "message_primary",
            "message_detail",
            "message_hint",
            "statement_position",
            "context",
            "schema_name",
            "table_name",
            "column_name",
            "datatype_name",
            "constraint_name",
            "source_file",
            "source_line",
            "source_function",
        ]:
            val = getattr(diag, attr, None)
            print(f"diag.{attr} =", val)
    traceback.print_exc()

print("\n--- attempt via DSN ---")
try:
    conn = psycopg2.connect(dsn, connect_timeout=5)
    print("connected ok (dsn)")
    conn.close()
except Exception as e:
    show_error(e)

print("\n--- attempt via explicit params ---")
try:
    conn = psycopg2.connect(
        host="localhost",  # try IPv6/IPv4 resolution
        port=5432,
        dbname="chatdb",
        user="postgres",
        password="postgres",
        connect_timeout=5,
    )
    print("connected ok (explicit)")
    conn.close()
except Exception as e:
    show_error(e)

print("\n--- attempt forcing IPv4 + disable ssl ---")
try:
    conn = psycopg2.connect(
        host="127.0.0.1",
        port=5432,
        dbname="chatdb",
        user="postgres",
        password="postgres",
        connect_timeout=5,
        sslmode="disable",
    )
    print("connected ok (ipv4, sslmode=disable)")
    conn.close()
except Exception as e:
    show_error(e)