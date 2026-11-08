"""Short SQLite transactions; candidates are computed before acquiring a write lock."""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sqlite3


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def body_hash(request):
    return hashlib.sha256(encode(request.model_dump()).encode("utf-8")).hexdigest()


class SQLiteStore:
    def __init__(self, path):
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS timelines (
                    id TEXT PRIMARY KEY, active_revision INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS revisions (
                    timeline_id TEXT NOT NULL REFERENCES timelines(id),
                    revision INTEGER NOT NULL, snapshot TEXT NOT NULL,
                    PRIMARY KEY(timeline_id, revision));
                CREATE TABLE IF NOT EXISTS drafts (
                    id TEXT PRIMARY KEY, timeline_id TEXT NOT NULL REFERENCES timelines(id),
                    body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS commits (
                    timeline_id TEXT NOT NULL REFERENCES timelines(id), request_id TEXT NOT NULL,
                    body_hash TEXT NOT NULL, response TEXT NOT NULL,
                    PRIMARY KEY(timeline_id, request_id));
                CREATE TABLE IF NOT EXISTS creates (
                    request_id TEXT PRIMARY KEY, body_hash TEXT NOT NULL, response TEXT NOT NULL);
                CREATE TRIGGER IF NOT EXISTS revisions_no_update BEFORE UPDATE ON revisions
                    BEGIN SELECT RAISE(ABORT, 'Revisions are immutable'); END;
                CREATE TRIGGER IF NOT EXISTS revisions_no_delete BEFORE DELETE ON revisions
                    BEGIN SELECT RAISE(ABORT, 'Revisions are immutable'); END;
            """)

    @contextmanager
    def connection(self, write=False):
        db = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA synchronous=FULL")
        try:
            if write:
                db.execute("BEGIN IMMEDIATE")
            yield db
            if write:
                db.commit()
        except BaseException:
            if db.in_transaction:
                db.rollback()
            raise
        finally:
            db.close()
