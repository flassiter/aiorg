"""
Unit tests for the database module.

Tests cover all NoteDatabase methods including edge cases and error handling.
"""

import pytest
import sqlite3
import time
from pathlib import Path
from organizer.database import NoteDatabase


@pytest.fixture
def db():
    """Create an in-memory database for testing."""
    database = NoteDatabase(":memory:")
    yield database
    database.close()


@pytest.fixture
def db_with_notes(db):
    """Create a database pre-populated with test notes."""
    notes = [
        "Python programming tutorial",
        "JavaScript basics and advanced concepts",
        "Database design principles",
        "Machine learning with Python",
        "Web development guide"
    ]
    for note in notes:
        db.save_note(note)
    return db


def test_create_database():
    """Test that database schema is created correctly."""
    db = NoteDatabase(":memory:")
    cursor = db.conn.cursor()

    # Check notes table exists
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='notes'"
    )
    assert cursor.fetchone() is not None

    # Check notes_fts virtual table exists
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='notes_fts'"
    )
    assert cursor.fetchone() is not None

    # Check app_state table exists
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='app_state'"
    )
    assert cursor.fetchone() is not None

    # Check triggers exist
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger' AND name='notes_ai'"
    )
    assert cursor.fetchone() is not None

    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger' AND name='notes_ad'"
    )
    assert cursor.fetchone() is not None

    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger' AND name='notes_au'"
    )
    assert cursor.fetchone() is not None

    db.close()


def test_save_new_note(db):
    """Test saving a new note returns valid ID."""
    content = "This is a test note"
    note_id = db.save_note(content)

    # Verify valid ID returned
    assert note_id > 0
    assert isinstance(note_id, int)

    # Verify note can be retrieved
    note = db.load_note(note_id)
    assert note is not None
    assert note['content'] == content


def test_save_update_note(db):
    """Test updating an existing note."""
    # Create initial note
    original_content = "Original content"
    note_id = db.save_note(original_content)

    # Load and verify original
    note = db.load_note(note_id)
    assert note['content'] == original_content
    original_created_at = note['created_at']

    # Small delay to ensure updated_at changes (SQLite has second-level precision)
    time.sleep(1.1)

    # Update note
    updated_content = "Updated content"
    returned_id = db.save_note(updated_content, note_id)

    # Verify same ID returned
    assert returned_id == note_id

    # Verify content updated
    note = db.load_note(note_id)
    assert note['content'] == updated_content

    # Verify created_at unchanged but updated_at changed
    assert note['created_at'] == original_created_at
    assert note['updated_at'] != note['created_at']


def test_load_note(db):
    """Test loading a note by ID."""
    content = "Test note content"
    note_id = db.save_note(content)

    # Load note
    note = db.load_note(note_id)

    # Verify all fields present
    assert note is not None
    assert 'id' in note
    assert 'content' in note
    assert 'created_at' in note
    assert 'updated_at' in note

    # Verify values
    assert note['id'] == note_id
    assert note['content'] == content
    assert note['created_at'] is not None
    assert note['updated_at'] is not None


def test_load_nonexistent_note(db):
    """Test that loading a non-existent note returns None."""
    note = db.load_note(99999)
    assert note is None


def test_delete_note(db):
    """Test deleting a note."""
    # Create note
    note_id = db.save_note("Note to delete")

    # Verify it exists
    assert db.load_note(note_id) is not None

    # Delete it
    result = db.delete_note(note_id)
    assert result is True

    # Verify it's gone
    assert db.load_note(note_id) is None

    # Try deleting non-existent note
    result = db.delete_note(note_id)
    assert result is False


def test_search_notes_simple(db_with_notes):
    """Test simple search query."""
    # Search for "Python"
    results = db_with_notes.search_notes("Python")

    # Should find 2 notes containing "Python"
    assert len(results) == 2

    # Verify results contain the search term
    for result in results:
        assert "Python" in result['content']
        assert 'id' in result
        assert 'content' in result
        assert 'created_at' in result
        assert 'updated_at' in result
        assert 'rank' in result


def test_search_notes_phrase(db_with_notes):
    """Test phrase search with quotes."""
    # Add a note with specific phrase
    db_with_notes.save_note("Learn advanced Python programming techniques")

    # Search for phrase
    results = db_with_notes.search_notes('"Python programming"')

    # Should find notes with that phrase
    assert len(results) >= 1

    # Verify phrase is in results
    found = False
    for result in results:
        if "Python programming" in result['content']:
            found = True
    assert found


def test_search_notes_empty(db_with_notes):
    """Test search with no results."""
    results = db_with_notes.search_notes("nonexistent_term_xyz")

    # Should return empty list
    assert len(results) == 0
    assert isinstance(results, list)


def test_list_all_notes(db_with_notes):
    """Test listing all notes with pagination."""
    # List all notes
    results = db_with_notes.list_all_notes(limit=100, offset=0)

    # Should have 5 notes (from fixture)
    assert len(results) == 5

    # Verify structure
    for result in results:
        assert 'id' in result
        assert 'content' in result
        assert 'created_at' in result
        assert 'updated_at' in result

    # Test pagination - first 3
    results_page1 = db_with_notes.list_all_notes(limit=3, offset=0)
    assert len(results_page1) == 3

    # Test pagination - next 2
    results_page2 = db_with_notes.list_all_notes(limit=3, offset=3)
    assert len(results_page2) == 2

    # Verify no overlap
    page1_ids = {r['id'] for r in results_page1}
    page2_ids = {r['id'] for r in results_page2}
    assert len(page1_ids.intersection(page2_ids)) == 0


def test_fts_triggers(db):
    """Test that FTS triggers keep search index in sync."""
    # Insert a note
    content1 = "Initial searchable content"
    note_id = db.save_note(content1)

    # Verify it's searchable
    results = db.search_notes("searchable")
    assert len(results) == 1
    assert results[0]['id'] == note_id

    # Update the note
    content2 = "Modified different content"
    db.save_note(content2, note_id)

    # Old term should not be found
    results = db.search_notes("searchable")
    assert len(results) == 0

    # New term should be found
    results = db.search_notes("different")
    assert len(results) == 1
    assert results[0]['id'] == note_id
    assert results[0]['content'] == content2

    # Delete the note
    db.delete_note(note_id)

    # Should not be searchable anymore
    results = db.search_notes("different")
    assert len(results) == 0


def test_timestamps(db):
    """Test that created_at and updated_at timestamps work correctly."""
    # Create note
    content = "Test note"
    note_id = db.save_note(content)

    # Load and check timestamps
    note = db.load_note(note_id)
    created_at = note['created_at']
    updated_at = note['updated_at']

    # Both should exist
    assert created_at is not None
    assert updated_at is not None

    # Initially they should be equal
    assert created_at == updated_at

    # Wait a bit (SQLite has second-level precision)
    time.sleep(1.1)

    # Update note
    db.save_note("Updated content", note_id)

    # Load again
    note = db.load_note(note_id)

    # created_at should remain unchanged
    assert note['created_at'] == created_at

    # updated_at should be different (later)
    assert note['updated_at'] != created_at
    assert note['updated_at'] > created_at


def test_database_file_creation(tmp_path):
    """Test that database file and directories are created properly."""
    # Use temporary directory
    db_path = tmp_path / "test_data" / "notes.db"

    # Directory should not exist yet
    assert not db_path.parent.exists()

    # Create database
    db = NoteDatabase(str(db_path))

    # Directory and file should now exist
    assert db_path.parent.exists()
    assert db_path.exists()

    # Should be able to save and load
    note_id = db.save_note("Test content")
    note = db.load_note(note_id)
    assert note is not None

    db.close()


def test_path_expansion():
    """Test that ~ is expanded to home directory."""
    db_path = "~/.aiorg_test/test.db"
    db = NoteDatabase(db_path)

    # Verify path was expanded
    assert "~" not in db.db_path
    assert str(Path.home()) in db.db_path

    db.close()

    # Clean up
    Path(db.db_path).unlink()
    Path(db.db_path).parent.rmdir()


def test_save_note_with_invalid_note_id(db):
    """Test updating with non-existent note_id creates new note."""
    # Try to update non-existent note
    content = "New content"
    note_id = db.save_note(content, note_id=99999)

    # Should create new note with different ID
    assert note_id != 99999

    # Verify it was saved
    note = db.load_note(note_id)
    assert note is not None
    assert note['content'] == content


def test_search_notes_with_limit(db_with_notes):
    """Test search respects limit parameter."""
    # Add more notes with "test" in them
    for i in range(10):
        db_with_notes.save_note(f"Test note number {i}")

    # Search with limit
    results = db_with_notes.search_notes("test", limit=5)

    # Should only return 5 results
    assert len(results) <= 5


def test_empty_database_operations(db):
    """Test operations on empty database."""
    # List all notes - should be empty
    results = db.list_all_notes()
    assert len(results) == 0

    # Search - should be empty
    results = db.search_notes("anything")
    assert len(results) == 0

    # Delete non-existent - should return False
    assert db.delete_note(1) is False

    # Load non-existent - should return None
    assert db.load_note(1) is None


def test_special_characters_in_content(db):
    """Test saving and searching notes with special characters."""
    special_content = "Test with 'quotes' and \"double quotes\" and <tags> & symbols!"
    note_id = db.save_note(special_content)

    # Should load correctly
    note = db.load_note(note_id)
    assert note['content'] == special_content

    # Should be searchable
    results = db.search_notes("quotes")
    assert len(results) == 1
    assert results[0]['id'] == note_id


def test_unicode_content(db):
    """Test saving and searching notes with Unicode characters."""
    unicode_content = "Testing Unicode: 你好 🌟 Ñoño café"
    note_id = db.save_note(unicode_content)

    # Should load correctly
    note = db.load_note(note_id)
    assert note['content'] == unicode_content

    # Should be searchable
    results = db.search_notes("Unicode")
    assert len(results) == 1


def test_large_content(db):
    """Test saving and loading large note content."""
    # Create a large note (1MB of text)
    large_content = "A" * (1024 * 1024)
    note_id = db.save_note(large_content)

    # Should load correctly
    note = db.load_note(note_id)
    assert note['content'] == large_content
    assert len(note['content']) == 1024 * 1024


def test_close_database(db):
    """Test closing database connection."""
    # Save a note
    note_id = db.save_note("Test")
    assert note_id > 0

    # Close database
    db.close()

    # Should not be able to use after closing
    with pytest.raises(sqlite3.ProgrammingError):
        db.save_note("After close")
