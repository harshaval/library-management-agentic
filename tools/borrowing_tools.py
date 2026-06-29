"""
tools/borrowing_tools.py
Loan lifecycle: checkout, return, and overdue reporting.
Queries use the partial index on loans(returned_on) for fast active-loan lookups.
"""

import json
from crewai.tools import tool
from db.database import get_connection


def _ok(**kwargs) -> str:
    return json.dumps({"result": "success", **kwargs})


def _err(detail: str) -> str:
    return json.dumps({"result": "error", "detail": detail})


@tool("checkout_book")
def checkout_book(member_email: str, isbn: str) -> str:
    """
    Borrow a book for a library member.
    Pass the member's email and the book's ISBN.
    Loan period is 14 days. Fails if no copies are available or records not found.
    """
    conn = get_connection()
    try:
        book = conn.execute(
            "SELECT id, title, available FROM books WHERE isbn=?", (isbn.strip(),)
        ).fetchone()
        if not book:
            return _err(f"No book found with ISBN '{isbn}'.")
        if book["available"] < 1:
            return _err(f"'{book['title']}' has no copies currently available.")

        member = conn.execute(
            "SELECT id, name FROM members WHERE email=?", (member_email.strip(),)
        ).fetchone()
        if not member:
            return _err(f"Member '{member_email}' not found.")

        # Single atomic write: insert loan + decrement available
        conn.execute(
            """INSERT INTO loans (book_id, member_id) VALUES (?, ?)""",
            (book["id"], member["id"]),
        )
        conn.execute(
            "UPDATE books SET available=available-1 WHERE id=?", (book["id"],)
        )
        conn.commit()
        return _ok(member=member["name"], book=book["title"], due_in="14 days")
    except Exception as exc:
        conn.rollback()
        return _err(str(exc))


@tool("return_book")
def return_book(member_email: str, isbn: str) -> str:
    """
    Return a borrowed book.
    Pass the member's email and the book's ISBN.
    Stamps the most recent active loan as returned and restores available count.
    """
    conn = get_connection()
    try:
        loan = conn.execute(
            """SELECT l.id, b.title, b.id AS book_id
               FROM   loans   l
               JOIN   books   b ON b.id = l.book_id
               JOIN   members m ON m.id = l.member_id
               WHERE  m.email=? AND b.isbn=? AND l.returned_on IS NULL
               ORDER  BY l.borrowed_on DESC
               LIMIT  1""",
            (member_email.strip(), isbn.strip()),
        ).fetchone()

        if not loan:
            return _err("No active loan found for that member + ISBN combination.")

        conn.execute(
            "UPDATE loans SET returned_on=date('now') WHERE id=?", (loan["id"],)
        )
        conn.execute(
            "UPDATE books SET available=available+1 WHERE id=?", (loan["book_id"],)
        )
        conn.commit()
        return _ok(returned=loan["title"])
    except Exception as exc:
        conn.rollback()
        return _err(str(exc))


@tool("list_overdue")
def list_overdue() -> str:
    """
    List all loans that are past their due date and not yet returned.
    Returns member name, email, book title, due date, and days overdue.
    No arguments required.
    """
    rows = get_connection().execute(
        """SELECT m.name, m.email, b.title, l.due_on,
                  CAST(julianday('now') - julianday(l.due_on) AS INTEGER) AS days_overdue
           FROM   loans   l
           JOIN   books   b ON b.id = l.book_id
           JOIN   members m ON m.id = l.member_id
           WHERE  l.returned_on IS NULL AND l.due_on < date('now')
           ORDER  BY days_overdue DESC"""
    ).fetchall()

    return _ok(overdue_count=len(rows), loans=[dict(r) for r in rows])
