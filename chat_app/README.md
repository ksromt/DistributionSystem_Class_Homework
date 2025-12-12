# Python + PostgreSQL Simple Chat Room (Example for Task 2)

## 1. Environment Setup

- Python 3.10+ (virtual environment recommended)  
- PostgreSQL (local or Docker)

```powershell
cd C:\drive_temp\DistrubuteSystem\12.9\chat_app

# 1) Create and activate virtual environment (PowerShell)
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
. .venv\Scripts\Activate.ps1

# 2) Install dependencies
pip install -r requirements.txt

# 3) Set database connection string (modify user/db as needed)
$env:DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:5432/chatdb?sslmode=disable"
```

> If database `chatdb` does not exist, create it first: `createdb -h localhost -U postgres chatdb`  
> Or run in `psql`: `CREATE DATABASE chatdb;`

## 2. Initialize Database

The server automatically creates tables on startup. If you want to create them manually beforehand, run:

```bash
python server.py
```

On first startup, tables `users`, `messages` and indexes will be created.

## 3. Start Server

```powershell
python server.py
```

- Default listening on `http://127.0.0.1:5000`, adjustable via environment variable `PORT`.  
- Health check: `GET /ping` returns `{"status": "ok"}`.  
- **It is recommended to keep the server running in one terminal and execute client commands in another terminal.**
- The server logs all events (register/login/post/retrieve) to stdout for easy demo observation.

## 4. Client Demo (CLI)

The client calls server APIs via HTTP:

```powershell
# Register two users
python cli_client.py register --username alice --password 123
python cli_client.py register --username bob --password 123

# Login to get user_id (returned in JSON as "id")
python cli_client.py login --username alice --password 123
python cli_client.py login --username bob --password 123

# Send messages (use respective user_id)
python cli_client.py say --user-id 1 --content "Hello from Alice"
python cli_client.py say --user-id 2 --content "Hi Alice, this is Bob"

# Retrieve recent messages
python cli_client.py list --limit 20
```

> Note: This example does not implement complex authentication/tokens. `user_id` is passed directly as a demo parameter. For better security, you could issue a simple token after login and verify it in message APIs.

## 5. Troubleshooting

- Ensure virtual environment is activated: `pip list` should show flask/psycopg2/requests.  
- Verify database connectivity: `python -c "import psycopg2; import os; print(os.environ['DATABASE_URL'])"`. If needed, verify using `psql`.  
- Ensure the server is running without errors (check the terminal running `server.py`); the client must be run in **a separate terminal**.  
- If port conflict, change port: `$env:PORT=8000; python server.py`, client uses `--api-url http://127.0.0.1:8000`.

## 6. Main API Endpoints (Brief)

- `POST /register`: `{"username", "password"}`, returns user info on success.  
- `POST /login`: `{"username", "password"}`, returns user info on success.  
- `POST /messages`: `{"user_id", "content"}`, writes message to DB.  
- `GET /messages?limit=20`: Lists recent messages in descending time order.
