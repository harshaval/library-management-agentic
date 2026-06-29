"""
tools/recommend_tools.py
Recommendation helpers: genre filtering and borrowing-history lookup.
"""

import json
from crewai.tools import tool
from db.database import get_connection


def _ok(**kwargs) -> str:
    return json.dumps({"result": "success", **kwargs})


def _err(detail: str) -> str:
    return json.dumps({"result": "error", "detail": detail})


@tool("books_by_genre")
def books_by_genre(genre: str) -> str:
    """
    Return all currently available books matching a genre (case-insensitive).
    Pass a genre string such as 'Science Fiction', 'Fantasy', 'Non-Fiction'.
    Results are sorted newest first.
    """
    rows = get_connection().execute(
        """SELECT id, title, author, genre, year, available
           FROM   books
           WHERE  genre LIKE ? AND available > 0
           ORDER  BY year DESC""",
        (f"%{genre.strip()}%",),
    ).fetchall()

    if not rows:
        return _err(f"No available books found for genre '{genre}'.")
    return _ok(genre=genre, count=len(rows), books=[dict(r) for r in rows])


@tool("member_borrow_history")
def member_borrow_history(member_email: str) -> str:
    """
    Retrieve a member's full borrowing history ordered most-recent first.
    Pass the member's email address. Useful for personalised recommendations.
    """
    conn = get_connection()
    member = conn.execute(
        "SELECT id, name FROM members WHERE email=?", (member_email.strip(),)
    ).fetchone()

    if not member:
        return _err(f"Member '{member_email}' not found.")

    rows = conn.execute(
        """SELECT b.title, b.author, b.genre, l.borrowed_on
           FROM   loans l
           JOIN   books b ON b.id = l.book_id
           WHERE  l.member_id=?
           ORDER  BY l.borrowed_on DESC""",
        (member["id"],),
    ).fetchall()

    return _ok(
        member=member["name"],
        history=[dict(r) for r in rows],
        note="" if rows else "No borrowing history yet.",
    )
