"""
main.py
Entry point. Loads env, initialises DB, builds the crew, runs the REPL.

Usage:
    python main.py
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()  # must run before any module that reads env vars

from db.database import init_db
from crew import build_crew, run

_BANNER = """
╔══════════════════════════════════════════╗
║     Library Book Management System       ║
║        Powered by CrewAI + Claude        ║
╚══════════════════════════════════════════╝

Sample requests:
  • Search for books by George Orwell
  • Check out '1984' for alice@example.com
  • Return '1984' for alice@example.com
  • Recommend a science fiction book for bob@example.com
  • Show overdue loans
  • Give me a library report

Type 'exit' to quit.
"""

_EXIT_CMDS = {"exit", "quit", "q", "bye"}


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit(
            "[Error] ANTHROPIC_API_KEY is not set.\n"
            "Copy .env.example to .env and add your key, then retry."
        )

    print(_BANNER)
    print("[System] Initialising database ...")
    init_db()

    print("[System] Building crew (this takes a moment on first run) ...")
    crew = build_crew()
    print("[System] Ready.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[System] Goodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in _EXIT_CMDS:
            print("[System] Goodbye!")
            break

        print()
        try:
            response = run(crew, user_input)
            print(f"Library AI:\n{response}\n")
        except Exception as exc:
            print(f"[Error] {exc}\n")
        print("─" * 60)


if __name__ == "__main__":
    main()
