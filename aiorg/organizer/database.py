"""
Database module for note storage and full-text search.

Implements SQLite-based note persistence with FTS5 full-text search.
"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional


logger = logging.getLogger(__name__)


class NoteDatabase:
    """Manages SQLite database operations for notes."""

    def __init__(self, db_path: str):
        """
        Initialize database connection and create schema.

        Args:
            db_path: Path to SQLite database file (supports ~ expansion)

        Raises:
            sqlite3.Error: If database connection or schema creation fails
        """
        # Expand ~ to home directory
        expanded_path = Path(db_path).expanduser()

        # Create parent directory if it doesn't exist
        expanded_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initializing database at {expanded_path}")

        try:
            self.db_path = str(expanded_path)
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row  # Return rows as dictionaries

            # Create schema
            self._create_schema()

            logger.info("Database initialized successfully")

        except sqlite3.Error as e:
            logger.error(f"Failed to initialize database: {e}", exc_info=True)
            raise

    def _create_schema(self):
        """Create database schema if tables don't exist."""
        cursor = self.conn.cursor()

        try:
            # Notes table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Full-text search virtual table
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
                    content,
                    content='notes',
                    content_rowid='id'
                )
            """)

            # Trigger: Sync FTS on INSERT
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON notes BEGIN
                    INSERT INTO notes_fts(rowid, content) VALUES (new.id, new.content);
                END
            """)

            # Trigger: Sync FTS on DELETE
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS notes_ad AFTER DELETE ON notes BEGIN
                    INSERT INTO notes_fts(notes_fts, rowid, content) VALUES('delete', old.id, old.content);
                END
            """)

            # Trigger: Sync FTS on UPDATE
            # Note: FTS5 requires special delete/insert syntax for external content tables
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS notes_au AFTER UPDATE ON notes BEGIN
                    INSERT INTO notes_fts(notes_fts, rowid, content) VALUES('delete', old.id, old.content);
                    INSERT INTO notes_fts(rowid, content) VALUES (new.id, new.content);
                END
            """)

            # App state table (for future use)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS app_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            self.conn.commit()
            logger.debug("Database schema created/verified")

        except sqlite3.Error as e:
            logger.error(f"Failed to create schema: {e}", exc_info=True)
            raise

    def save_note(self, content: str, note_id: Optional[int] = None) -> int:
        """
        Save note to database.

        Args:
            content: Markdown content
            note_id: If provided, update existing note; otherwise create new

        Returns:
            int: Note ID

        Raises:
            sqlite3.Error: If save operation fails
        """
        cursor = self.conn.cursor()

        try:
            if note_id is None:
                # Create new note
                cursor.execute(
                    "INSERT INTO notes (content) VALUES (?)",
                    (content,)
                )
                note_id = cursor.lastrowid
                self.conn.commit()
                logger.info(f"Created new note ID {note_id} ({len(content)} chars)")

            else:
                # Update existing note with explicit timestamp
                cursor.execute(
                    "UPDATE notes SET content = ?, updated_at = datetime('now') WHERE id = ?",
                    (content, note_id)
                )

                if cursor.rowcount == 0:
                    logger.warning(f"Note ID {note_id} not found, creating new note")
                    # Note doesn't exist, create it
                    cursor.execute(
                        "INSERT INTO notes (content) VALUES (?)",
                        (content,)
                    )
                    note_id = cursor.lastrowid

                self.conn.commit()
                logger.info(f"Updated note ID {note_id} ({len(content)} chars)")

            return note_id

        except sqlite3.Error as e:
            logger.error(f"Failed to save note: {e}", exc_info=True)
            self.conn.rollback()
            raise

    def load_note(self, note_id: int) -> Optional[dict]:
        """
        Load note by ID.

        Args:
            note_id: Note ID to load

        Returns:
            dict: {'id', 'content', 'created_at', 'updated_at'} or None

        Raises:
            sqlite3.Error: If load operation fails
        """
        cursor = self.conn.cursor()

        try:
            cursor.execute(
                "SELECT id, content, created_at, updated_at FROM notes WHERE id = ?",
                (note_id,)
            )

            row = cursor.fetchone()

            if row is None:
                logger.debug(f"Note ID {note_id} not found")
                return None

            note = dict(row)
            logger.debug(f"Loaded note ID {note_id} ({len(note['content'])} chars)")
            return note

        except sqlite3.Error as e:
            logger.error(f"Failed to load note {note_id}: {e}", exc_info=True)
            raise

    def search_notes(self, query: str, limit: int = 50) -> list[dict]:
        """
        Full-text search across notes.

        Args:
            query: Search query (FTS5 syntax supported)
            limit: Maximum results to return

        Returns:
            list[dict]: List of note dictionaries with search ranking

        Raises:
            sqlite3.Error: If search operation fails
        """
        cursor = self.conn.cursor()

        try:
            # Use FTS5 MATCH for full-text search
            # Join with notes table to get all fields
            cursor.execute("""
                SELECT
                    notes.id,
                    notes.content,
                    notes.created_at,
                    notes.updated_at,
                    notes_fts.rank
                FROM notes_fts
                JOIN notes ON notes.id = notes_fts.rowid
                WHERE notes_fts MATCH ?
                ORDER BY notes_fts.rank
                LIMIT ?
            """, (query, limit))

            results = [dict(row) for row in cursor.fetchall()]
            logger.info(f"Search for '{query}' returned {len(results)} results")
            return results

        except sqlite3.Error as e:
            logger.error(f"Failed to search notes with query '{query}': {e}", exc_info=True)
            raise

    def delete_note(self, note_id: int) -> bool:
        """
        Delete note by ID.

        Args:
            note_id: Note ID to delete

        Returns:
            bool: True if note was deleted, False if not found

        Raises:
            sqlite3.Error: If delete operation fails
        """
        cursor = self.conn.cursor()

        try:
            cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
            deleted = cursor.rowcount > 0
            self.conn.commit()

            if deleted:
                logger.info(f"Deleted note ID {note_id}")
            else:
                logger.debug(f"Note ID {note_id} not found for deletion")

            return deleted

        except sqlite3.Error as e:
            logger.error(f"Failed to delete note {note_id}: {e}", exc_info=True)
            self.conn.rollback()
            raise

    def list_all_notes(self, limit: int = 100, offset: int = 0) -> list[dict]:
        """
        List all notes with pagination.

        Args:
            limit: Maximum results to return
            offset: Number of results to skip

        Returns:
            list[dict]: List of note dictionaries ordered by updated_at DESC

        Raises:
            sqlite3.Error: If list operation fails
        """
        cursor = self.conn.cursor()

        try:
            cursor.execute("""
                SELECT id, content, created_at, updated_at
                FROM notes
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))

            results = [dict(row) for row in cursor.fetchall()]
            logger.debug(f"Listed {len(results)} notes (limit={limit}, offset={offset})")
            return results

        except sqlite3.Error as e:
            logger.error(f"Failed to list notes: {e}", exc_info=True)
            raise

    def close(self):
        """Close database connection."""
        try:
            if self.conn:
                self.conn.close()
                logger.info("Database connection closed")
        except sqlite3.Error as e:
            logger.error(f"Error closing database connection: {e}", exc_info=True)
            raise
