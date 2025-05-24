import pytest
from typer.testing import CliRunner
from tasks.cli import app, get_json_content, set_json_content
from datetime import datetime, timedelta

runner = CliRunner()

def add_mock_tasks():
    tasks = [
        {"id": 1, "name": "Task 1", "priority": "low", "status": "todo", "due_date": None},
        {"id": 2, "name": "Task 2", "priority": "high", "status": "in_progress", "due_date": (datetime.now() + timedelta(days=1)).isoformat()},
        {"id": 3, "name": "Task 3", "priority": "medium", "status": "done", "due_date": (datetime.now() - timedelta(days=1)).isoformat()},
    ]
    set_json_content(tasks)

def clear_mock_tasks():
    set_json_content([])

@pytest.fixture(autouse=True)
def setup_and_teardown():
    clear_mock_tasks()
    yield
    clear_mock_tasks()

def test_adds_task_with_valid_data():
    result = runner.invoke(app, ["add", "New Task", "--priority", "medium", "--due", (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')])
    assert result.exit_code == 0
    assert "Task 'New Task' added." in result.output
    tasks = get_json_content()
    assert len(tasks) == 1
    assert tasks[0]["name"] == "New Task"

def test_fails_to_add_task_with_past_due_date():
    result = runner.invoke(app, ["add", "Invalid Task", "--due", (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')])
    assert result.exit_code != 0
    assert "Due date cannot be in the past." in result.output

def test_lists_all_tasks():
    add_mock_tasks()
    result = runner.invoke(app, ["show"])
    assert result.exit_code == 0
    assert "Task 1" in result.output
    assert "Task 2" in result.output
    assert "Task 3" in result.output

def test_filters_tasks_by_status():
    add_mock_tasks()
    result = runner.invoke(app, ["show", "--status", "todo"])
    assert result.exit_code == 0
    assert "Task 1" in result.output
    assert "Task 2" not in result.output
    assert "Task 3" not in result.output

def test_updates_task_with_valid_data():
    add_mock_tasks()
    result = runner.invoke(app, ["update", "1", "--name", "Updated Task", "--priority", "high"])
    assert result.exit_code == 0
    assert "Task '1' updated." in result.output
    tasks = get_json_content()
    assert tasks[0]["name"] == "Updated Task"
    assert tasks[0]["priority"] == "high"

def test_fails_to_update_task_with_invalid_id():
    result = runner.invoke(app, ["update", "999", "--name", "Nonexistent Task"])
    assert result.exit_code != 0
    assert "Task with ID '999' not found." in result.output

def test_closes_task_successfully():
    add_mock_tasks()
    result = runner.invoke(app, ["close", "1"])
    assert result.exit_code == 0
    assert "Task '1' closed." in result.output
    tasks = get_json_content()
    assert tasks[0]["status"] == "done"

def test_deletes_task_successfully():
    add_mock_tasks()
    result = runner.invoke(app, ["close", "1", "--delete"])
    assert result.exit_code == 0
    assert "Task '1' deleted." in result.output
    tasks = get_json_content()
    assert len(tasks) == 2