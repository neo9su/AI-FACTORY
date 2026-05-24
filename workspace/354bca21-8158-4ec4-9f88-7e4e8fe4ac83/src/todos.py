#!/usr/bin/env python3
"""Todo CLI tool - core implementation."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.table import Table
from rich.text import Text

logger = logging.getLogger(__name__)

# Default JSON file path
DEFAULT_TODOS_FILE = "todos.json"


@dataclass
class Todo:
    """Represents a single todo item."""
    id: int
    title: str
    completed: bool = False


class TodoStore:
    """Manages persistence of todos in a JSON file."""

    def __init__(self, file_path: str | Path) -> None:
        self.file_path = Path(file_path)
        self._todos: List[Todo] = []
        self._next_id: int = 1
        self._load()

    def _load(self) -> None:
        """Load todos from JSON file. If file doesn't exist, start empty."""
        if not self.file_path.exists():
            logger.info("No existing todos file found, starting fresh.")
            self._todos = []
            self._next_id = 1
            return

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error("Failed to load todos file: %s", e)
            sys.exit(1)

        if not isinstance(data, dict):
            logger.error("Invalid todos file format: expected a dict")
            sys.exit(1)

        todos_data = data.get("todos", [])
        if not isinstance(todos_data, list):
            logger.error("Invalid todos file format: 'todos' must be a list")
            sys.exit(1)

        self._todos = []
        for item in todos_data:
            if not isinstance(item, dict):
                logger.warning("Skipping invalid todo entry: %s", item)
                continue
            todo = Todo(
                id=item.get("id", 0),
                title=item.get("title", ""),
                completed=item.get("completed", False),
            )
            self._todos.append(todo)

        self._next_id = data.get("next_id", max((t.id for t in self._todos), default=0) + 1)

    def _save(self) -> None:
        """Save todos to JSON file."""
        data = {
            "todos": [asdict(t) for t in self._todos],
            "next_id": self._next_id,
        }
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except OSError as e:
            logger.error("Failed to save todos file: %s", e)
            sys.exit(1)

    def add(self, title: str) -> Todo:
        """Add a new todo with the given title.

        Args:
            title: The title of the todo.

        Returns:
            The newly created Todo.
        """
        if not title or not title.strip():
            logger.error("Todo title cannot be empty")
            sys.exit(1)

        todo = Todo(id=self._next_id, title=title.strip())
        self._next_id += 1
        self._todos.append(todo)
        self._save()
        logger.info("Added todo: %s", todo.title)
        return todo

    def list_todos(self) -> List[Todo]:
        """Return all todos."""
        return self._todos

    def complete(self, todo_id: int) -> Optional[Todo]:
        """Mark a todo as completed by its ID.

        Args:
            todo_id: The ID of the todo to complete.

        Returns:
            The updated Todo if found, None otherwise.
        """
        for todo in self._todos:
            if todo.id == todo_id:
                todo.completed = True
                self._save()
                logger.info("Completed todo: %s", todo.title)
                return todo
        logger.warning("Todo with ID %d not found", todo_id)
        return None

    def delete(self, todo_id: int) -> bool:
        """Delete a todo by its ID.

        Args:
            todo_id: The ID of the todo to delete.

        Returns:
            True if deleted, False if not found.
        """
        for i, todo in enumerate(self._todos):
            if todo.id == todo_id:
                del self._todos[i]
                self._save()
                logger.info("Deleted todo: %s", todo.title)
                return True
        logger.warning("Todo with ID %d not found", todo_id)
        return False


def get_todos_file_path() -> Path:
    """Get the todos file path from environment variable or default."""
    env_path = os.environ.get("TODOS_FILE")
    if env_path:
        return Path(env_path)
    return Path(DEFAULT_TODOS_FILE)


def display_todos(console: Console, todos: List[Todo]) -> None:
    """Display todos in a rich table with colored status."""
    if not todos:
        console.print("[yellow]No todos found.[/yellow]")
        return

    table = Table(title="Todos")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Title")
    table.add_column("Status")

    for todo in todos:
        status = Text("✓ Complete", style="green") if todo.completed else Text("✗ Incomplete", style="red")
        table.add_row(str(todo.id), todo.title, status)

    console.print(table)


def main() -> None:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(description="Simple CLI Todo Manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Add command
    add_parser = subparsers.add_parser("add", help="Add a new todo")
    add_parser.add_argument("title", type=str, help="Title of the todo")

    # List command
    subparsers.add_parser("list", help="List all todos")

    # Complete command
    complete_parser = subparsers.add_parser("complete", help="Mark a todo as completed")
    complete_parser.add_argument("id", type=int, help="ID of the todo to complete")

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a todo")
    delete_parser.add_argument("id", type=int, help="ID of the todo to delete")

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    # Initialize store
    file_path = get_todos_file_path()
    store = TodoStore(file_path)
    console = Console()

    if args.command == "add":
        todo = store.add(args.title)
        console.print(f"[green]Added todo:[/green] {todo.title} (ID: {todo.id})")
    elif args.command == "list":
        todos = store.list_todos()
        display_todos(console, todos)
    elif args.command == "complete":
        todo = store.complete(args.id)
        if todo:
            console.print(f"[green]Completed:[/green] {todo.title}")
        else:
            console.print(f"[red]Todo with ID {args.id} not found.[/red]")
    elif args.command == "delete":
        deleted = store.delete(args.id)
        if deleted:
            console.print(f"[green]Deleted todo with ID {args.id}.[/green]")
        else:
            console.print(f"[red]Todo with ID {args.id} not found.[/red]")


if __name__ == "__main__":
    main()
