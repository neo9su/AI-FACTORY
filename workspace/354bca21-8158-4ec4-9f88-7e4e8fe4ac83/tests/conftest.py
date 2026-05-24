import pytest
import tempfile
import json
from pathlib import Path
from src.todos import TodoStore, Todo


@pytest.fixture
def temp_store():
    """Create a TodoStore with a temporary JSON file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(json.dumps({"todos": [], "next_id": 1}))
        temp_path = f.name
    store = TodoStore(temp_path)
    yield store
    Path(temp_path).unlink(missing_ok=True)


@pytest.fixture
def sample_store(temp_store):
    """Pre-populate store with sample todos."""
    temp_store.add("Buy groceries")
    temp_store.add("Read a book")
    temp_store.add("Write code")
    return temp_store
