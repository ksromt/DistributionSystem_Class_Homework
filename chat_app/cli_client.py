import argparse
import os
import sys
from typing import Any, Dict

import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL", "http://127.0.0.1:5000")


def pretty_print(resp: requests.Response):
    try:
        data = resp.json()
    except Exception:
        print(resp.text)
        return
    print(f"[{resp.status_code}] {data}")


def do_register(args: argparse.Namespace):
    payload = {"username": args.username, "password": args.password}
    resp = requests.post(f"{API_URL}/register", json=payload)
    pretty_print(resp)


def do_login(args: argparse.Namespace):
    payload = {"username": args.username, "password": args.password}
    resp = requests.post(f"{API_URL}/login", json=payload)
    pretty_print(resp)


def do_say(args: argparse.Namespace):
    payload = {"user_id": args.user_id, "content": args.content}
    resp = requests.post(f"{API_URL}/messages", json=payload)
    pretty_print(resp)


def do_list(args: argparse.Namespace):
    params: Dict[str, Any] = {"limit": args.limit}
    resp = requests.get(f"{API_URL}/messages", params=params)
    pretty_print(resp)


def main():
    global API_URL  # declared early to avoid "used prior to global declaration"
    parser = argparse.ArgumentParser(description="Simple chat client for the Python + PostgreSQL demo.")
    parser.add_argument(
        "--api-url",
        default=API_URL,
        help="Server base URL (default: %(default)s). Can also set env API_URL.",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    reg = sub.add_parser("register", help="register a user")
    reg.add_argument("--username", required=True)
    reg.add_argument("--password", required=True)
    reg.set_defaults(func=do_register)

    login = sub.add_parser("login", help="login a user")
    login.add_argument("--username", required=True)
    login.add_argument("--password", required=True)
    login.set_defaults(func=do_login)

    say = sub.add_parser("say", help="send a message")
    say.add_argument("--user-id", type=int, required=True)
    say.add_argument("--content", required=True)
    say.set_defaults(func=do_say)

    lst = sub.add_parser("list", help="list recent messages")
    lst.add_argument("--limit", type=int, default=20)
    lst.set_defaults(func=do_list)

    args = parser.parse_args()
    # Override API_URL if provided by flag.
    API_URL = args.api_url

    args.func(args)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)



