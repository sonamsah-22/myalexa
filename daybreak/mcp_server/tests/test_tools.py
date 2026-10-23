"""
Unit test suite for MyAlexa MCP tools using memory storage backend.
Covers normal functionality, empty-data states, and bad-input validation.
"""
import pytest
import datetime
from daybreak.mcp_server.storage import get_storage
from daybreak.mcp_server.tools.planner_tools import (
    add_event,
    get_agenda,
    add_task,
    list_tasks,
    complete_task,
    plan_my_day,
    resolve_date
)


@pytest.fixture(autouse=True)
def clean_storage():
    """Ensure clean memory storage before each test."""
    storage = get_storage()
    storage.clear_all()
    yield
    storage.clear_all()


def test_resolve_date_normalization_and_fallback():
    """Test date resolution for 'today', 'tomorrow', ISO dates, and invalid strings."""
    today = datetime.date.today().isoformat()
    tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
    assert resolve_date("today") == today
    assert resolve_date("tomorrow") == tomorrow
    assert resolve_date("2026-10-15") == "2026-10-15"
    assert resolve_date("invalid-date-format") == today


def test_add_event_success():
    """Test adding a normal non-overlapping event."""
    resp = add_event(title="Team Sync", date="today", start_time="10:00", end_time="11:00")
    assert "added Team Sync" in resp


def test_add_event_overlap_rejection():
    """Bad-input / constraint test: reject adding an event that overlaps an existing event."""
    add_event(title="Team Sync", date="today", start_time="10:00", end_time="11:00")
    resp_overlap = add_event(title="Client Call", date="today", start_time="10:30", end_time="11:30")
    assert "overlaps with your existing event 'Team Sync'" in resp_overlap


def test_add_event_bad_times():
    """Bad-input tests: end time before start time AND malformed time string '25:99'."""
    # End time before start time
    resp_invalid_range = add_event(title="Reverse Time", date="today", start_time="14:00", end_time="13:00")
    assert "start time must be before the end time" in resp_invalid_range

    # Malformed time string '25:99'
    resp_malformed = add_event(title="Bad Time", date="today", start_time="25:99", end_time="10:00")
    assert "time format is invalid" in resp_malformed


def test_get_agenda_empty_day():
    """Empty-data test: get_agenda on an empty day with no events or plans."""
    resp_empty = get_agenda(date="today")
    assert "no events or plans scheduled today" in resp_empty


def test_get_agenda_populated():
    """Normal test: get_agenda on a day with events and saved plan."""
    add_event(title="Coffee Break", date="today", start_time="14:00", end_time="14:30")
    resp_agenda = get_agenda(date="today")
    assert "You have one event today: Coffee Break at 14:00" in resp_agenda


def test_add_task_normal_and_empty_title():
    """Normal & Bad-input test: adding a task with valid title vs empty title."""
    resp_valid = add_task(title="buy groceries", due="today", duration_min=45)
    assert "Added task 'buy groceries'" in resp_valid

    # Bad input: empty title
    resp_empty = add_task(title="")
    assert "Please specify a title for the task" in resp_empty


def test_list_tasks_zero_and_overflow():
    """Empty-data & Overflow test: list_tasks with 0 tasks, <=5 tasks, and >5 tasks."""
    # Empty data case (0 tasks)
    assert "no pending tasks" in list_tasks()

    # <= 5 tasks
    add_task("task 1")
    add_task("task 2")
    resp_2 = list_tasks()
    assert "2 pending tasks: task 1 and task 2" in resp_2

    # > 5 tasks (overflow case showing 'and N more')
    add_task("task 3")
    add_task("task 4")
    add_task("task 5")
    add_task("task 6")
    add_task("task 7")
    resp_7 = list_tasks()
    assert "7 pending tasks" in resp_7
    assert "and 2 more" in resp_7


def test_complete_task_fuzzy_and_no_match():
    """Normal & Bad-input test: complete_task with fuzzy title match vs no match found."""
    add_task("Call dentist for checkup")
    
    # Fuzzy match success
    resp_done = complete_task("dentist")
    assert "marked 'Call dentist for checkup' as complete" in resp_done

    # Bad-input / missing task case: no match
    resp_no_match = complete_task("nonexistent task")
    assert "couldn't find a pending task" in resp_no_match


def test_plan_my_day_normal():
    """Normal test: plan_my_day scheduling pending tasks into available gaps."""
    add_event(title="Morning Meeting", date="today", start_time="10:00", end_time="11:00")
    add_task(title="Write code", duration_min=60)
    add_task(title="Review PRs", duration_min=30)
    
    plan_resp = plan_my_day(date="today")
    assert "planned your day" in plan_resp or "Write code" in plan_resp

    # Check plan storage
    storage = get_storage()
    saved = storage.get_plan(datetime.date.today().isoformat())
    assert saved is not None
    assert "summary" in saved


def test_plan_my_day_no_tasks_and_fully_booked():
    """Empty-data & Constraint tests: plan_my_day with no open tasks vs fully booked day."""
    # Case 1: No open tasks on calendar
    resp_no_tasks = plan_my_day(date="today")
    assert "no tasks to schedule" in resp_no_tasks

    # Case 2: Open tasks exist, but day is fully booked from 09:00 to 18:00
    add_event(title="All Day Hackathon", date="today", start_time="09:00", end_time="18:00")
    add_task(title="Try to fit this task", duration_min=30)
    resp_fully_booked = plan_my_day(date="today")
    assert "fully booked" in resp_fully_booked
