from enum import Enum
from datetime import datetime
from rich.table import Table
from rich.console import Console
from pathlib import Path

import json
import os
import typer
import sys

class PrioTask(str, Enum):
    """Priority of the task."""
    low = "low"
    medium = "medium"
    high = "high"

class TaskStatus(str, Enum):
    """Status of the task."""
    todo = "todo"
    in_progress = "in_progress"
    done = "done"

app = typer.Typer(help="Task management CLI")

@app.command()
def add(
    name: str = typer.Argument(..., help="Name of the task"),
    priority: PrioTask = typer.Option(PrioTask.low, "--priority", "-p", help="Priority of the task"),
    due_date: datetime = typer.Option(None, "--due", "-d", help="Due date of the task"),
    status: TaskStatus = typer.Option(TaskStatus.todo, "--status", "-s", help="Status of the task"),
):
    """Add a new task."""
    if due_date and due_date < datetime.now():
        raise typer.BadParameter("Due date cannot be in the past.")
    if status == TaskStatus.done:
        raise typer.BadParameter("Task cannot be created with status 'done'.")
    if priority not in PrioTask:
        raise typer.BadParameter(f"Invalid priority '{priority}'. Valid options are: {', '.join(PrioTask.__members__.keys())}.")
    if status not in TaskStatus:
        raise typer.BadParameter(f"Invalid status '{status}'. Valid options are: {', '.join(TaskStatus.__members__.keys())}.")
    if not name:
        raise typer.BadParameter("Task name cannot be empty.")

    tasks = get_json_content()

    if tasks:
        max_id = max(task["id"] for task in tasks)
    else:
        max_id = 0

    new_task = {
        "id": max_id + 1,
        "name": name,
        "priority": priority,
        "status": status,
       "due_date": due_date.isoformat() if due_date else None
    }

    tasks.append(new_task)

    set_json_content(tasks)

    typer.echo(f"Task '{name}' added.")

@app.command()
def show(
    status: TaskStatus = typer.Option(None, "--status", "-s", help="Filter tasks by status"),
    priority: PrioTask = typer.Option(None, "--priority", "-p", help="Filter tasks by priority"),
):
    """List all tasks."""

    tasks = get_json_content()

    if priority:
        tasks = [task for task in tasks if task["priority"] == priority]
    if status:
        tasks = [task for task in tasks if task["status"] == status]

    tasks.sort(key=lambda x: (
        [PrioTask.high, PrioTask.medium, PrioTask.low].index(x["priority"]),
        [TaskStatus.in_progress, TaskStatus.todo, TaskStatus.done].index(x["status"])
    ))

    for task in tasks:
        if task["priority"] == PrioTask.low:
            task["priority"] = "[green]low[/]"
        elif task["priority"] == PrioTask.medium:
            task["priority"] = "[yellow]medium[/]"
        elif task["priority"] == PrioTask.high:
            task["priority"] = "[red]high[/]"

    for task in tasks:
        if task["status"] == TaskStatus.todo:
            task["status"] = "[yellow]todo[/]"
        elif task["status"] == TaskStatus.in_progress:
            task["status"] = "[green]in progress[/]"
        elif task["status"] == TaskStatus.done:
            task["status"] = "[green]done[/]"

    for task in tasks:
        if task["due_date"]:
            if datetime.fromisoformat(task["due_date"]) > datetime.now():
                task["due_date"] = "[green]"+datetime.fromisoformat(task["due_date"]).strftime("%d-%m-%Y")+"[/]"
            else:
                task["due_date"] = "[red]"+datetime.fromisoformat(task["due_date"]).strftime("%d-%m-%Y")+"[/]"
        else:
            task["due_date"] = "N/A"

    table = Table(title=f"List of tasks", show_lines=True)
    table.add_column("ID", justify="right", style="white")
    table.add_column("Name", justify="left", style="white")
    table.add_column("Priority", justify="left", style="green")
    table.add_column("Status", justify="left", style="yellow")
    table.add_column("Due Date", justify="left", style="blue")

    if tasks:
        for task in tasks:
            table.add_row(
                str(task["id"]),
                task["name"],
                task["priority"],
                task["status"],
                task["due_date"] if task["due_date"] else "N/A"
            )
    else:
        typer.echo("No tasks found.")

    console = Console()
    console.print(table)

    if status:
        typer.echo(f"Listing tasks with status '{status}'.")
    else:
        typer.echo("Listing all tasks.")

@app.command()
def update(
    task_id: int = typer.Argument(..., help="ID of the task to update"),
    name: str = typer.Option(None, "--name", "-n", help="New name of the task"),
    priority: PrioTask = typer.Option(None, "--priority", "-p", help="New priority of the task"),
    due_date: datetime = typer.Option(None, "--due", "-d", help="New due date of the task"),
    status: TaskStatus = typer.Option(None, "--status", "-s", help="New status of the task"),
):
    """Update an existing task."""
    tasks = get_json_content()

    task = next((task for task in tasks if task["id"] == task_id), None)
    if not task:
        raise typer.BadParameter(f"Task with ID '{task_id}' not found.")
    if due_date and due_date < datetime.now():
        raise typer.BadParameter("Due date cannot be in the past.")
    if status == TaskStatus.done and task["status"] != TaskStatus.done:
        raise typer.BadParameter("Task cannot be updated to status 'done'.")
    if priority and priority not in PrioTask:
        raise typer.BadParameter(f"Invalid priority '{priority}'. Valid options are: {', '.join(PrioTask.__members__.keys())}.")
    if status and status not in TaskStatus:
        raise typer.BadParameter(f"Invalid status '{status}'. Valid options are: {', '.join(TaskStatus.__members__.keys())}.")
    if name:
        task["name"] = name
    if priority:
        task["priority"] = priority
    if due_date:
        task["due_date"] = due_date.isoformat()
    if status:
        task["status"] = status

    set_json_content(tasks)
    typer.echo(f"Task '{task_id}' updated.")


@app.command()
def close(
    task_id: int = typer.Argument(..., help="ID of the task to close"),
    is_delete: bool = typer.Option(False, "--delete", "-d", help="Delete the task instead of closing it"),
):
    """Close a task."""
    tasks = get_json_content()

    task = next((task for task in tasks if task["id"] == task_id), None)
    if not task:
        raise typer.BadParameter(f"Task with ID '{task_id}' not found.")
    if task["status"] == TaskStatus.done and not is_delete:
        raise typer.BadParameter(f"Task with ID '{task_id}' is already closed.")

    if is_delete:
        tasks.remove(task)
        set_json_content(tasks)
        typer.echo(f"Task '{task_id}' deleted.")
        return
    task["status"] = TaskStatus.done

    set_json_content(tasks)
    typer.echo(f"Task '{task_id}' closed.")


def get_json_content():
    """Get the content of a JSON file."""
    file =  Path.home() / "tasks.json"
    if "pytest" in sys.modules:
        file = Path.home() / "tasks_test.json"
    if os.path.exists(file):
        with open(file, 'r', encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    else:
        return []

def set_json_content(tasks):
    """Set the content of a JSON file."""
    file =  Path.home() / "tasks.json"
    if "pytest" in sys.modules:
        file = Path.home() / "tasks_test.json"
    with open(file, 'w', encoding='utf-8') as f:
        json.dump(tasks, f, indent=2, ensure_ascii=False)