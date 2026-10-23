"""
Voice-friendly MCP tools for the MyAlexa Daily Planner.
All responses return concise, spoken plain-text sentences suitable for text-to-speech.
"""
import os
import datetime
import logging
from typing import Dict, Any, List, Optional
from daybreak.mcp_server.storage import get_storage

logger = logging.getLogger(__name__)


def resolve_date(date_str: str) -> str:
    """Normalize human-friendly date keywords to ISO YYYY-MM-DD format."""
    if not date_str:
        return datetime.date.today().isoformat()
    
    cleaned = date_str.strip().lower()
    today = datetime.date.today()
    
    if cleaned in ("today", "now"):
        return today.isoformat()
    elif cleaned == "tomorrow":
        return (today + datetime.timedelta(days=1)).isoformat()
    elif cleaned == "yesterday":
        return (today - datetime.timedelta(days=1)).isoformat()
    
    # Try parsing ISO YYYY-MM-DD
    try:
        parsed = datetime.datetime.strptime(cleaned, "%Y-%m-%d").date()
        return parsed.isoformat()
    except ValueError:
        # Fallback to today if unparseable
        return today.isoformat()


def time_to_minutes(time_str: str) -> int:
    """Convert HH:MM string to minutes since midnight. Returns -1 if invalid format or out of bounds."""
    try:
        parts = time_str.strip().split(":")
        hours = int(parts[0])
        minutes = int(parts[1]) if len(parts) > 1 else 0
        if not (0 <= hours <= 23 and 0 <= minutes <= 59):
            return -1
        return hours * 60 + minutes
    except Exception:
        return -1


def minutes_to_time(minutes: int) -> str:
    """Convert minutes since midnight to HH:MM string."""
    hours = (minutes // 60) % 24
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"


def add_event(title: str, date: str = "today", start_time: str = "09:00", end_time: str = "10:00") -> str:
    """
    Use this tool when the user wants to add a calendar event, meeting, or appointment.
    Parameters:
      title: Name of the event.
      date: Date of the event ('today', 'tomorrow', or 'YYYY-MM-DD').
      start_time: Start time in HH:MM format (e.g., '10:00').
      end_time: End time in HH:MM format (e.g., '11:00').
    Returns a brief spoken confirmation or rejection if overlapping.
    """
    try:
        storage = get_storage()
        iso_date = resolve_date(date)
        
        start_min = time_to_minutes(start_time)
        end_min = time_to_minutes(end_time)
        
        if start_min < 0 or end_min < 0:
            return "I couldn't add that event because the time format is invalid. Please use HH:MM format."

        if start_min >= end_min:
            return "I couldn't add that event because the start time must be before the end time."
            
        existing_events = storage.get_events(iso_date)
        for ev in existing_events:
            ev_start = time_to_minutes(ev.get("start", "00:00"))
            ev_end = time_to_minutes(ev.get("end", "00:00"))
            
            # Check overlap: max(start1, start2) < min(end1, end2)
            if max(start_min, ev_start) < min(end_min, ev_end):
                return (
                    f"I couldn't add '{title}' because it overlaps with your existing event "
                    f"'{ev.get('title')}' scheduled from {ev.get('start')} to {ev.get('end')}."
                )

        storage.add_event(title=title, date=iso_date, start_time=start_time, end_time=end_time)
        date_word = "today" if iso_date == datetime.date.today().isoformat() else f"for {iso_date}"
        return f"I've added {title} to your schedule {date_word} from {start_time} to {end_time}."
    except Exception as e:
        logger.error(f"Error in add_event: {e}")
        return "Sorry, I ran into an error while adding that event."


def get_agenda(date: str = "today") -> str:
    """
    Use this tool when the user asks for their agenda, schedule, or what's on their calendar for a day.
    Parameters:
      date: The date to query ('today', 'tomorrow', or 'YYYY-MM-DD').
    Returns a 1-3 sentence spoken summary of events and tasks.
    """
    try:
        storage = get_storage()
        iso_date = resolve_date(date)
        events = storage.get_events(iso_date)
        plan = storage.get_plan(iso_date)
        
        date_label = "today" if iso_date == datetime.date.today().isoformat() else f"on {iso_date}"
        
        if not events and not plan:
            return f"You have no events or plans scheduled {date_label}."
            
        parts = []
        if events:
            event_strs = [f"{ev['title']} at {ev['start']}" for ev in events[:3]]
            if len(events) == 1:
                parts.append(f"You have one event {date_label}: {event_strs[0]}.")
            else:
                parts.append(f"You have {len(events)} events {date_label}: {', '.join(event_strs)}.")
                
        if plan and plan.get("summary"):
            parts.append(f"Your plan: {plan['summary']}")
            
        return " ".join(parts)
    except Exception as e:
        logger.error(f"Error in get_agenda: {e}")
        return "Sorry, I couldn't fetch your agenda right now."


def add_task(title: str, due: str = "", duration_min: int = 30) -> str:
    """
    Use this tool when the user wants to add a to-do item or task to their list.
    Parameters:
      title: The description of the task (e.g., 'call dentist', 'buy groceries').
      due: Optional due date or time ('today', 'tomorrow', or 'YYYY-MM-DD').
      duration_min: Estimated duration in minutes (default is 30).
    Returns a spoken confirmation.
    """
    try:
        if not title or not title.strip():
            return "Please specify a title for the task."
            
        storage = get_storage()
        due_date = resolve_date(due) if due else ""
        storage.add_task(title=title.strip(), due=due_date, duration_min=duration_min)
        
        if due_date:
            return f"Added task '{title}' to your to-do list, due {due_date}."
        return f"Added task '{title}' to your to-do list."
    except Exception as e:
        logger.error(f"Error in add_task: {e}")
        return "Sorry, I couldn't save that task."


def list_tasks() -> str:
    """
    Use this tool when the user asks for their to-do list, pending tasks, or tasks to complete.
    Returns a spoken list of up to 5 items, plus 'and N more' if there are additional tasks.
    """
    try:
        storage = get_storage()
        tasks = storage.list_tasks(include_completed=False)
        
        if not tasks:
            return "You have no pending tasks on your to-do list."
            
        titles = [t["title"] for t in tasks]
        total = len(titles)
        
        if total <= 5:
            if total == 1:
                return f"You have 1 pending task: {titles[0]}."
            elif total == 2:
                return f"You have 2 pending tasks: {titles[0]} and {titles[1]}."
            else:
                formatted_items = ", ".join(titles[:-1]) + f", and {titles[-1]}"
                return f"You have {total} pending tasks: {formatted_items}."
        else:
            shown = ", ".join(titles[:5])
            remaining = total - 5
            return f"You have {total} pending tasks: {shown}, and {remaining} more."
    except Exception as e:
        logger.error(f"Error in list_tasks: {e}")
        return "Sorry, I couldn't retrieve your tasks right now."


def complete_task(title_or_id: str) -> str:
    """
    Use this tool when the user says they completed, finished, or done a task.
    Parameters:
      title_or_id: The title or ID of the task to mark completed.
    Returns a spoken confirmation.
    """
    try:
        if not title_or_id or not title_or_id.strip():
            return "Please specify which task you completed."
            
        storage = get_storage()
        completed = storage.complete_task(title_or_id)
        
        if completed:
            return f"Great job! I've marked '{completed['title']}' as complete."
        else:
            return f"I couldn't find a pending task matching '{title_or_id}' in your list."
    except Exception as e:
        logger.error(f"Error in complete_task: {e}")
        return "Sorry, I ran into a problem completing that task."


def plan_my_day(date: str = "today") -> str:
    """
    Use this tool when the user asks to plan their day, optimize their schedule, or organize tasks into free slots.
    Parameters:
      date: The date to plan ('today', 'tomorrow', or 'YYYY-MM-DD').
    Returns a 2-3 sentence spoken plan summary after assigning pending tasks into free calendar gaps between 09:00 and 18:00.
    """
    try:
        storage = get_storage()
        iso_date = resolve_date(date)
        events = storage.get_events(iso_date)
        open_tasks = storage.list_tasks(include_completed=False)
        
        # Define working window: 09:00 (540 min) to 18:00 (1080 min)
        DAY_START = 540  # 09:00
        DAY_END = 1080  # 18:00
        
        # Convert events to minute ranges
        event_ranges = []
        for ev in events:
            s_min = max(DAY_START, min(DAY_END, time_to_minutes(ev.get("start", "09:00"))))
            e_min = max(DAY_START, min(DAY_END, time_to_minutes(ev.get("end", "18:00"))))
            if s_min < e_min:
                event_ranges.append((s_min, e_min, ev.get("title", "Event")))
                
        event_ranges.sort(key=lambda x: x[0])
        
        # Calculate free gaps between 09:00 and 18:00
        gaps = []
        current_pos = DAY_START
        for s_min, e_min, _ in event_ranges:
            if s_min > current_pos:
                gaps.append((current_pos, s_min))
            current_pos = max(current_pos, e_min)
            
        if current_pos < DAY_END:
            gaps.append((current_pos, DAY_END))
            
        # Fit open tasks into gaps using shortest-fit / greedy approach
        assigned_schedule = []
        unassigned_tasks = []
        
        # Copy tasks list so we can pop
        remaining_tasks = list(open_tasks)
        
        for gap_start, gap_end in gaps:
            gap_duration = gap_end - gap_start
            slot_cursor = gap_start
            
            i = 0
            while i < len(remaining_tasks):
                task = remaining_tasks[i]
                dur = int(task.get("duration_min", 30))
                if dur <= (gap_end - slot_cursor):
                    t_start = slot_cursor
                    t_end = slot_cursor + dur
                    assigned_schedule.append({
                        "task_id": task.get("id"),
                        "title": task.get("title"),
                        "start": minutes_to_time(t_start),
                        "end": minutes_to_time(t_end),
                        "duration_min": dur
                    })
                    slot_cursor += dur
                    remaining_tasks.pop(i)
                else:
                    i += 1
                    
        # Any remaining tasks couldn't fit
        unassigned_tasks = remaining_tasks
        
        # Build raw deterministic summary
        if not open_tasks and not events:
            summary = "Your day is completely wide open between 9 AM and 6 PM with no tasks to schedule."
        elif not open_tasks:
            summary = f"You have {len(events)} calendar events scheduled, but no open tasks on your to-do list."
        elif not assigned_schedule:
            summary = "Your schedule is fully booked today between 9 AM and 6 PM, so none of your pending tasks could fit."
        else:
            task_summaries = [f"{item['title']} from {item['start']} to {item['end']}" for item in assigned_schedule[:3]]
            summary = f"I've planned your day! I scheduled {', '.join(task_summaries)}."
            if len(assigned_schedule) > 3:
                summary += f" Plus {len(assigned_schedule) - 3} more tasks in your open slots."
                
        # Optional Amazon Bedrock polishing step
        bedrock_model_id = os.getenv("BEDROCK_MODEL_ID")
        if bedrock_model_id and os.getenv("AWS_REGION"):
            try:
                import boto3
                client = boto3.client("bedrock-runtime", region_name=os.getenv("AWS_REGION", "us-east-1"))
                prompt = (
                    f"Rephrase the following schedule summary into 2 short, natural spoken sentences for Alexa. "
                    f"Do not use markdown, lists, or extra intro text.\n"
                    f"Scheduled items: {summary}"
                )
                response = client.converse(
                    modelId=bedrock_model_id,
                    messages=[{"role": "user", "content": [{"text": prompt}]}],
                    inferenceConfig={"maxTokens": 100, "temperature": 0.3}
                )
                bedrock_text = response["output"]["message"]["content"][0]["text"].strip()
                if bedrock_text:
                    summary = bedrock_text
            except Exception as b_err:
                logger.warning(f"Bedrock converse unavailable or failed ({b_err}), using deterministic summary fallback.")

        # Save plan to storage
        storage.save_plan(date=iso_date, summary=summary, schedule=assigned_schedule)
        return summary
    except Exception as e:
        logger.error(f"Error in plan_my_day: {e}")
        return "Sorry, I was unable to generate your daily plan right now."
