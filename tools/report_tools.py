"""
tools/report_tools.py
Aggregate reporting: headline stats and most-borrowed rankings.
Both queries run in a single round-trip where possible.
"""

import json
from crewai.tools import tool
from db.database import get_connection


def _ok(**kwargs) -> str:
    return json.dumps({"result": "success", **kwargs})


def _err(detail: str) -> str:
    return json.dumps({"result": "error", "detail": detail})


@tool("library_stats")
def library_stats() -> str:
    """
    Return headline library statistics: total titles, copies, members,
    active loans, overdue loans, and books returned this month.
    No arguments required.
    """
    conn = get_connection()
    try:
        # One query covers all scalar metrics via conditional aggregation
        row = conn.execute(
            """SELECT
                 (SELECT COUNT(*)        FROM books)   AS total_titles,
                 (SELECT SUM(copies)     FROM books)   AS total_copies,
                 (SELECT COUNT(*)        FROM members) AS total_members,
                 (SELECT COUNT(*) FROM loans WHERE returned_on IS NULL)
                                                       AS active_loans,
                 (SELECT COUNT(*) FROM loans
                  WHERE returned_on IS NULL AND due_on < date('now'))
                                                       AS overdue_loans,
                 (SELECT COUNT(*) FROM loans
                  WHERE returned_on >= date('now','start of month'))
                                                       AS returned_this_month"""
        ).fetchone()
        return _ok(stats=dict(row))
    except Exception as exc:
        return _err(str(exc))


@tool("most_borrowed_books")
def most_borrowed_books(limit: int = 5) -> str:
    """
    Return the top N most-borrowed books of all time.
    Pass limit (integer, default 5).
    """
    try:
        rows = get_connection().execute(
            """SELECT b.title, b.author, b.genre, COUNT(l.id) AS borrow_count
               FROM   loans l
               JOIN   books b ON b.id = l.book_id
               GROUP  BY l.book_id
               ORDER  BY borrow_count DESC
               LIMIT  ?""",
            (max(1, int(limit)),),
        ).fetchall()

        if not rows:
            return _ok(books=[], note="No loan history yet.")
        return _ok(top_n=len(rows), books=[dict(r) for r in rows])
    except Exception as exc:
        return _err(str(exc))
