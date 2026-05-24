import pytest
import json
from pathlib import Path
from src.todos import TodoStore, Todo


class TestTodoStore:
    """Tests for TodoStore class."""

    def test_add_todo(self, temp_store):
        """Test adding a todo."""
        todo = temp_store.add("Test task")
        assert todo.id == 1
        assert todo.title == "Test task"
        assert todo.completed is False
        assert len(temp_store.list_todos()) == 1

    def test_add_empty_title(self, temp_store):
        """Test adding a todo with empty title exits."""
        with pytest.raises(SystemExit):
            temp_store.add("")

    def test_add_whitespace_title(self, temp_store):
        """Test adding a todo with whitespace-only title exits."""
        with pytest.raises(SystemExit):
            temp_store.add("   ")

    def test_list_todos_empty(self, temp_store):
        """Test listing when no todos exist."""
        assert temp_store.list_todos() == []

    def test_list_todos(self, sample_store):
        """Test listing todos."""
        todos = sample_store.list_todos()
        assert len(todos) == 3
        titles = [t.title for t in todos]
        assert "Buy groceries" in titles
        assert "Read a book" in titles
        assert "Write code" in titles

    def test_complete_todo(self, sample_store):
        """Test completing a todo."""
        todo = sample_store.complete(1)
        assert todo is not None
        assert todo.completed is True
        # Verify persistence
        todos = sample_store.list_todos()
        completed = [t for t in todos if t.completed]
        assert len(completed) == 1
        assert completed[0].id == 1

    def test_complete_nonexistent(self, sample_store):
        """Test completing a non-existent todo returns None."""
        result = sample_store.complete(999)
        assert result is None

    def test_delete_todo(self, sample_store):
        """Test deleting a todo."""
        deleted = sample_store.delete(2)
        assert deleted is True
        todos = sample_store.list_todos()
        assert len(todos) == 2
        ids = [t.id for t in todos]
        assert 2 not in ids

    def test_delete_nonexistent(self, sample_store):
        """Test deleting a non-existent todo returns False."""
        result = sample_store.delete(999)
        assert result is False

    def test_persistence(self, temp_store):
        """Test that todos are persisted to file."""
        temp_store.add("Persist me")
        # Create a new store pointing to the same file
        store2 = TodoStore(temp_store.file_path)
        todos = store2.list_todos()
        assert len(todos) == 1
        assert todos[0].title == "Persist me"

    def test_load_invalid_json(self):
        """Test loading an invalid JSON file exits."""
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not json")
            temp_path = f.name
        with pytest.raises(SystemExit):
            TodoStore(temp_path)
        Path(temp_path).unlink(missing_ok=True)

    def test_load_missing_file(self, tmp_path):
        """Test loading a non-existent file starts fresh."""
        non_existent = tmp_path / "nonexistent.json"
        store = TodoStore(non_existent)
        assert store.list_todos() == []
        assert store._next_id == 1

    def test_next_id_increment(self, temp_store):
        """Test that IDs increment correctly."""
        t1 = temp_store.add("First")
        t2 = temp_store.add("Second")
        assert t1.id == 1
        assert t2.id == 2

    def test_delete_updates_file(self, sample_store):
        """Test that deleting a todo updates the JSON file."""
        sample_store.delete(1)
        with open(sample_store.file_path, "r") as f:
            data = json.load(f)
        assert len(data["todos"]) == 2
        ids = [t["id"] for t in data["todos"]]
        assert 1 not in ids

    def test_complete_updates_file(self, sample_store):
        """Test that completing a todo updates the JSON file."""
        sample_store.complete(1)
        with open(sample_store.file_path, "r") as f:
            data = json.load(f)
        completed = [t for t in data["todos"] if t["completed"]]
        assert len(completed) == 1
        assert completed[0]["id"] == 1
