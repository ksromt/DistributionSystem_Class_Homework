import hashlib
import logging
import os
from contextlib import closing
from typing import Any, Dict, List

from flask import Flask, jsonify, request
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load environment variables from a .env file if present.
load_dotenv()

# Configure basic logging to stdout for demo visibility.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

app = Flask(__name__)

# Example: postgresql://user:pass@localhost:5432/chatdb
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/chatdb")


def get_connection():
    """
    Create a new database connection.
    A simple per-request connection is sufficient for this toy program.
    """
    return psycopg2.connect(DATABASE_URL, connect_timeout=5)


def init_db():
    """
    Initialize tables if they do not exist.
    """
    ddl = """
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(64) UNIQUE NOT NULL,
        password_hash VARCHAR(128) NOT NULL,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS messages (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        content TEXT NOT NULL,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages (created_at DESC);
    """
    with closing(get_connection()) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(ddl)
    log_event("database ready (tables ensured)")


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def log_event(message: str, **kwargs: Any) -> None:
    """
    Log a short event with structured context for demo visibility.
    """
    if kwargs:
        app.logger.info("%s | %s", message, kwargs)
    else:
        app.logger.info(message)


@app.route("/ping", methods=["GET"])
def ping():
    log_event("ping")
    return jsonify({"status": "ok"})


@app.route("/register", methods=["POST"])
def register():
    data = request.get_json(force=True)
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        log_event("register rejected (missing fields)", username=username)
        return jsonify({"error": "username and password are required"}), 400

    pw_hash = hash_password(password)

    try:
        with closing(get_connection()) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO users (username, password_hash)
                    VALUES (%s, %s)
                    RETURNING id, username, created_at
                    """,
                    (username, pw_hash),
                )
                row = cur.fetchone()
                conn.commit()
                log_event("user registered", user_id=row["id"], username=row["username"])
                return jsonify({"user": row}), 201
    except psycopg2.errors.UniqueViolation:
        log_event("register failed (duplicate)", username=username)
        return jsonify({"error": "username already exists"}), 400
    except Exception as exc:  # pragma: no cover - simple error fallback
        log_event("register failed (exception)", username=username, error=str(exc))
        return jsonify({"error": str(exc)}), 500


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(force=True)
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        log_event("login rejected (missing fields)", username=username)
        return jsonify({"error": "username and password are required"}), 400

    pw_hash = hash_password(password)

    with closing(get_connection()) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, username
                FROM users
                WHERE username = %s AND password_hash = %s
                """,
                (username, pw_hash),
            )
            row = cur.fetchone()
            if not row:
                log_event("login failed (invalid credentials)", username=username)
                return jsonify({"error": "invalid credentials"}), 401
            log_event("login success", user_id=row["id"], username=row["username"])
            return jsonify({"user": row})


@app.route("/messages", methods=["POST"])
def post_message():
    data = request.get_json(force=True)
    user_id = data.get("user_id")
    content = (data.get("content") or "").strip()

    if not user_id or not content:
        log_event("post_message rejected (missing fields)", user_id=user_id)
        return jsonify({"error": "user_id and content are required"}), 400

    with closing(get_connection()) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO messages (user_id, content)
                VALUES (%s, %s)
                RETURNING id, user_id, content, created_at
                """,
                (user_id, content),
            )
            row = cur.fetchone()
            conn.commit()
            log_event("message posted", user_id=row["user_id"], message_id=row["id"])
            return jsonify({"message": row}), 201


@app.route("/messages", methods=["GET"])
def list_messages():
    try:
        limit = int(request.args.get("limit", 20))
    except ValueError:
        log_event("list_messages rejected (bad limit)")
        return jsonify({"error": "limit must be an integer"}), 400
    limit = max(1, min(limit, 200))

    with closing(get_connection()) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT m.id, m.content, m.created_at, u.username, u.id AS user_id
                FROM messages m
                JOIN users u ON u.id = m.user_id
                ORDER BY m.created_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows: List[Dict[str, Any]] = cur.fetchall()
            log_event("list_messages", limit=limit, returned=len(rows))
            return jsonify({"messages": rows})


if __name__ == "__main__":
    init_db()
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)



