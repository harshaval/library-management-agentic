"""
tools/catalog_tools.py
Catalog operations: search, add, update.
All tools reuse the per-thread connection from get_connection() and
return JSON strings so the LLM can reason over structured data.
"""

import json
from crewai.tools import tool
from db.database import get_connection

_ALLOWED_UPDATE_FIELDS = frozenset({"genre", "description", "copies", "year"})


def _ok(**kwargs) -> str:
    return json.dumps({"result": "success", **kwargs})


def _err(detail: str) -> str:
    return json.dumps({"result": "error", "detail": detail})


@tool("search_catalog")
def search_catalog(query: str) -> str:
    """
    Search the book catalog by title, author, genre, or ISBN.
    Pass a plain search term e.g. 'Orwell', 'Science Fiction', or an ISBN.
    Returns up to 10 matching books as JSON.
    """
    term = f"%{query.strip()}%"
    rows = get_connection().execute(
        """SELECT id, isbn, title, author, genre, year, copies, available
           FROM   books
           WHERE  title  LIKE ? OR author LIKE ?
              OR  genre  LIKE ? OR isbn   LIKE ?
           LIMIT  10""",
        (term, term, term, term),
    ).fetchall()

    if not rows:
        return _err(f"No books found for query: '{query}'")
    return _ok(count=len(rows), books=[dict(r) for r in rows])


@tool("add_book")
def add_book(
    isbn: str,
    title: str,
    author: str,
    genre: str,
    year: int,
    copies: int = 1,
    description: str = "",
) -> str:
    """
    Add a new book to the catalog.
    Required: isbn, title, author, genre, year.
    Optional: copies (default 1), description.
    """
    if copies < 1:
        return _err("copies must be at least 1.")
    conn = get_connection()
    try:
        cur = conn.execute(
            """INSERT INTO books
                   (isbn, title, author, genre, year, copies, available, description)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (isbn.strip(), title.strip(), author.strip(),
             genre.strip(), int(year), copies, copies, description.strip()),
        )
        conn.commit()
        return _ok(book_id=cur.lastrowid, title=title)
    except Exception as exc:
        return _err(str(exc))


@tool("update_book")
def update_book(book_id: int, field: str, value: str) -> str:
    """
    Update one field on an existing book.
    Allowed fields: genre, description, copies, year.
    Pass book_id (int), field name, and the new value as a string.
    """
    if field not in _ALLOWED_UPDATE_FIELDS:
        return _err(f"'{field}' is not editable. Allowed: {sorted(_ALLOWED_UPDATE_FIELDS)}")

    conn = get_connection()
    try:
        cast = int(value) if field in {"copies", "year"} else value
        conn.execute(f"UPDATE books SET {field}=? WHERE id=?", (cast, book_id))

        # Keep available in sync when total copies change
        if field == "copies":
            conn.execute(
                """UPDATE books
                   SET    available = ? - (
                       SELECT COUNT(*) FROM loans
                       WHERE  book_id=? AND returned_on IS NULL
                   )
                   WHERE  id=?""",
                (cast, book_id, book_id),
            )
        conn.commit()
        return _ok(book_id=book_id, updated={field: value})
    except Exception as exc:
        return _err(str(exc))
