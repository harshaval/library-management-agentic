"""
db/database.py
Thread-safe SQLite layer using a module-level connection pool (one
connection per thread via threading.local). PRAGMAs are set once per
connection rather than on every query, cutting per-call overhead.
"""

import sqlite3
import threading
from pathlib import Path

DB_PATH = Path(__file__).parent / "library.db"

_local = threading.local()


def get_connection() -> sqlite3.Connection:
    """
    Return the per-thread SQLite connection, creating it on first access.
    Reusing one connection per thread avoids the overhead of opening /
    closing a file handle on every tool call.
    """
    if not getattr(_local, "conn", None):
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # Set PRAGMAs once per connection
        conn.executescript(
            "PRAGMA journal_mode=WAL;"
            "PRAGMA foreign_keys=ON;"
            "PRAGMA synchronous=NORMAL;"   # safe with WAL, faster than FULL
            "PRAGMA cache_size=-8000;"     # 8 MB page cache per connection
        )
        _local.conn = conn
    return _local.conn


# ---------------------------------------------------------------------------
# Schema + seed data
# ---------------------------------------------------------------------------

_SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    isbn        TEXT    UNIQUE NOT NULL,
    title       TEXT    NOT NULL,
    author      TEXT    NOT NULL,
    genre       TEXT    NOT NULL DEFAULT 'General',
    year        INTEGER,
    copies      INTEGER NOT NULL DEFAULT 1,
    available   INTEGER NOT NULL DEFAULT 1,
    description TEXT    NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS members (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    name      TEXT NOT NULL,
    email     TEXT UNIQUE NOT NULL,
    joined_on TEXT NOT NULL DEFAULT (date('now'))
);

CREATE TABLE IF NOT EXISTS loans (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id     INTEGER NOT NULL REFERENCES books(id),
    member_id   INTEGER NOT NULL REFERENCES members(id),
    borrowed_on TEXT NOT NULL DEFAULT (date('now')),
    due_on      TEXT NOT NULL DEFAULT (date('now', '+14 days')),
    returned_on TEXT
);

CREATE INDEX IF NOT EXISTS idx_loans_book      ON loans(book_id);
CREATE INDEX IF NOT EXISTS idx_loans_member    ON loans(member_id);
CREATE INDEX IF NOT EXISTS idx_loans_active    ON loans(returned_on) WHERE returned_on IS NULL;
CREATE INDEX IF NOT EXISTS idx_books_isbn      ON books(isbn);
CREATE INDEX IF NOT EXISTS idx_books_genre     ON books(genre);
"""

_SEED_BOOKS = [
    ("978-0-06-112008-4", "To Kill a Mockingbird", "Harper Lee",
     "Fiction", 1960, 3, "A story of racial injustice and childhood innocence in Alabama."),
    ("978-0-7432-7356-5", "1984", "George Orwell",
     "Dystopia", 1949, 2, "A totalitarian future where Big Brother surveils everything."),
    ("978-0-14-028329-7", "The Great Gatsby", "F. Scott Fitzgerald",
     "Fiction", 1925, 2, "The American dream through the eyes of Jay Gatsby."),
    ("978-0-14-243723-0", "Sapiens", "Yuval Noah Harari",
     "Non-Fiction", 2011, 4, "A brief history of humankind from the Stone Age to today."),
    ("978-0-525-55360-5", "Dune", "Frank Herbert",
     "Science Fiction", 1965, 3, "Epic sci-fi set on the desert planet Arrakis."),
    ("978-1-78633-600-4", "Atomic Habits", "James Clear",
     "Self-Help", 2018, 5, "Proven framework for building good habits and breaking bad ones."),
    ("978-0-374-52965-5", "The Name of the Wind", "Patrick Rothfuss",
     "Fantasy", 2007, 2, "The legendary Kvothe recounts his extraordinary life."),
    ("978-0-385-54734-9", "Project Hail Mary", "Andy Weir",
     "Science Fiction", 2021, 3, "A lone astronaut must save Earth from an extinction threat."),
]

_SEED_MEMBERS = [
    ("Alice Sharma", "alice@example.com"),
    ("Bob Rao",      "bob@example.com"),
]


def init_db() -> None:
    """Create schema and seed data. Safe to call multiple times (idempotent)."""
    conn = get_connection()
    conn.executescript(_SCHEMA)

    conn.executemany(
        """INSERT OR IGNORE INTO books
               (isbn, title, author, genre, year, copies, available, description)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        [(isbn, title, author, genre, year, copies, copies, desc)
         for isbn, title, author, genre, year, copies, desc in _SEED_BOOKS],
    )
    conn.executemany(
        "INSERT OR IGNORE INTO members (name, email) VALUES (?, ?)",
        _SEED_MEMBERS,
    )
    conn.commit()
    print(f"[DB] Ready → {DB_PATH}")


if __name__ == "__main__":
    init_db()
