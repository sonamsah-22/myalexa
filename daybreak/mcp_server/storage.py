"""
Storage abstraction for MyAlexa planner backend.
Supports in-memory storage (default, zero AWS setup) and DynamoDB single-table backend.
"""
import os
import uuid
import datetime
from typing import List, Dict, Any, Optional, Protocol


DEMO_USER_PK = "USER#demo"


class StorageBackend(Protocol):
    """Protocol defining the storage interface for planner items."""
    
    def add_event(self, title: str, date: str, start_time: str, end_time: str) -> Dict[str, Any]:
        ...
        
    def get_events(self, date: str) -> List[Dict[str, Any]]:
        ...
        
    def add_task(self, title: str, due: str = "", duration_min: int = 30) -> Dict[str, Any]:
        ...
        
    def list_tasks(self, include_completed: bool = False) -> List[Dict[str, Any]]:
        ...
        
    def complete_task(self, title_or_id: str) -> Optional[Dict[str, Any]]:
        ...
        
    def save_plan(self, date: str, summary: str, schedule: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        ...
        
    def get_plan(self, date: str) -> Optional[Dict[str, Any]]:
        ...
        
    def clear_all(self) -> None:
        ...


class MemoryStorage:
    """In-memory implementation of planner storage."""
    
    def __init__(self):
        # Map (pk, sk) -> dict item
        self._store: Dict[tuple, Dict[str, Any]] = {}

    def add_event(self, title: str, date: str, start_time: str, end_time: str) -> Dict[str, Any]:
        event_id = str(uuid.uuid4())[:8]
        sk = f"EVENT#{date}#{event_id}"
        item = {
            "pk": DEMO_USER_PK,
            "sk": sk,
            "id": event_id,
            "title": title,
            "date": date,
            "start": start_time,
            "end": end_time,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        self._store[(DEMO_USER_PK, sk)] = item
        return item

    def get_events(self, date: str) -> List[Dict[str, Any]]:
        prefix = f"EVENT#{date}#"
        events = []
        for (pk, sk), item in self._store.items():
            if pk == DEMO_USER_PK and sk.startswith(prefix):
                events.append(item)
        # Sort by start time
        events.sort(key=lambda x: x.get("start", ""))
        return events

    def add_task(self, title: str, due: str = "", duration_min: int = 30) -> Dict[str, Any]:
        task_id = str(uuid.uuid4())[:8]
        sk = f"TASK#{task_id}"
        item = {
            "pk": DEMO_USER_PK,
            "sk": sk,
            "id": task_id,
            "title": title,
            "due": due,
            "duration_min": duration_min,
            "done": False,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        self._store[(DEMO_USER_PK, sk)] = item
        return item

    def list_tasks(self, include_completed: bool = False) -> List[Dict[str, Any]]:
        tasks = []
        for (pk, sk), item in self._store.items():
            if pk == DEMO_USER_PK and sk.startswith("TASK#"):
                if include_completed or not item.get("done", False):
                    tasks.append(item)
        # Sort tasks by due date / title
        tasks.sort(key=lambda x: (x.get("done", False), x.get("due") or "9999", x.get("title", "")))
        return tasks

    def complete_task(self, title_or_id: str) -> Optional[Dict[str, Any]]:
        target_key = None
        target_item = None
        
        # Exact ID match first
        for (pk, sk), item in self._store.items():
            if pk == DEMO_USER_PK and sk.startswith("TASK#"):
                if item.get("id") == title_or_id or sk == f"TASK#{title_or_id}":
                    target_key = (pk, sk)
                    target_item = item
                    break
        
        # Fuzzy title match if not found by ID
        if not target_item:
            query_lower = title_or_id.strip().lower()
            best_match = None
            best_score = -1
            
            for (pk, sk), item in self._store.items():
                if pk == DEMO_USER_PK and sk.startswith("TASK#") and not item.get("done", False):
                    title_lower = item.get("title", "").strip().lower()
                    if query_lower in title_lower:
                        # Exact match gets score 100, substring match gets score based on length
                        score = 100 if query_lower == title_lower else 50
                        if score > best_score:
                            best_score = score
                            best_match = ((pk, sk), item)
            
            if best_match:
                target_key, target_item = best_match

        if target_item and target_key:
            target_item["done"] = True
            self._store[target_key] = target_item
            return target_item

        return None

    def save_plan(self, date: str, summary: str, schedule: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        sk = f"PLAN#{date}"
        item = {
            "pk": DEMO_USER_PK,
            "sk": sk,
            "date": date,
            "summary": summary,
            "schedule": schedule or [],
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        self._store[(DEMO_USER_PK, sk)] = item
        return item

    def get_plan(self, date: str) -> Optional[Dict[str, Any]]:
        sk = f"PLAN#{date}"
        return self._store.get((DEMO_USER_PK, sk))

    def clear_all(self) -> None:
        self._store.clear()


class DynamoDBStorage:
    """DynamoDB single-table implementation of planner storage."""

    def __init__(self, table_name: Optional[str] = None):
        import boto3
        table_name = table_name or os.getenv("DYNAMODB_TABLE_NAME", "planner")
        region = os.getenv("AWS_REGION", "us-east-1")
        dynamodb = boto3.resource("dynamodb", region_name=region)
        self.table = dynamodb.Table(table_name)

    def add_event(self, title: str, date: str, start_time: str, end_time: str) -> Dict[str, Any]:
        event_id = str(uuid.uuid4())[:8]
        sk = f"EVENT#{date}#{event_id}"
        item = {
            "pk": DEMO_USER_PK,
            "sk": sk,
            "id": event_id,
            "title": title,
            "date": date,
            "start": start_time,
            "end": end_time,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        self.table.put_item(Item=item)
        return item

    def get_events(self, date: str) -> List[Dict[str, Any]]:
        from boto3.dynamodb.conditions import Key
        prefix = f"EVENT#{date}#"
        response = self.table.query(
            KeyConditionExpression=Key("pk").eq(DEMO_USER_PK) & Key("sk").begins_with(prefix)
        )
        items = response.get("Items", [])
        items.sort(key=lambda x: x.get("start", ""))
        return items

    def add_task(self, title: str, due: str = "", duration_min: int = 30) -> Dict[str, Any]:
        task_id = str(uuid.uuid4())[:8]
        sk = f"TASK#{task_id}"
        item = {
            "pk": DEMO_USER_PK,
            "sk": sk,
            "id": task_id,
            "title": title,
            "due": due,
            "duration_min": duration_min,
            "done": False,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        self.table.put_item(Item=item)
        return item

    def list_tasks(self, include_completed: bool = False) -> List[Dict[str, Any]]:
        from boto3.dynamodb.conditions import Key
        response = self.table.query(
            KeyConditionExpression=Key("pk").eq(DEMO_USER_PK) & Key("sk").begins_with("TASK#")
        )
        items = response.get("Items", [])
        if not include_completed:
            items = [t for t in items if not t.get("done", False)]
        items.sort(key=lambda x: (x.get("done", False), x.get("due") or "9999", x.get("title", "")))
        return items

    def complete_task(self, title_or_id: str) -> Optional[Dict[str, Any]]:
        all_tasks = self.list_tasks(include_completed=False)
        target = None
        
        # Match by ID
        for task in all_tasks:
            if task.get("id") == title_or_id or task.get("sk") == f"TASK#{title_or_id}":
                target = task
                break

        # Fuzzy match by title
        if not target:
            query_lower = title_or_id.strip().lower()
            for task in all_tasks:
                if query_lower in task.get("title", "").strip().lower():
                    target = task
                    break

        if target:
            response = self.table.update_item(
                Key={"pk": DEMO_USER_PK, "sk": target["sk"]},
                UpdateExpression="SET done = :val",
                ExpressionAttributeValues={":val": True},
                ReturnValues="ALL_NEW"
            )
            return response.get("Attributes", target)

        return None

    def save_plan(self, date: str, summary: str, schedule: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        sk = f"PLAN#{date}"
        item = {
            "pk": DEMO_USER_PK,
            "sk": sk,
            "date": date,
            "summary": summary,
            "schedule": schedule or [],
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        self.table.put_item(Item=item)
        return item

    def get_plan(self, date: str) -> Optional[Dict[str, Any]]:
        response = self.table.get_item(Key={"pk": DEMO_USER_PK, "sk": f"PLAN#{date}"})
        return response.get("Item")

    def clear_all(self) -> None:
        from boto3.dynamodb.conditions import Key
        response = self.table.query(
            KeyConditionExpression=Key("pk").eq(DEMO_USER_PK)
        )
        for item in response.get("Items", []):
            self.table.delete_item(Key={"pk": item["pk"], "sk": item["sk"]})


_global_storage_instance = None

def get_storage() -> StorageBackend:
    """Factory function returning configured storage instance based on STORAGE env var."""
    global _global_storage_instance
    if _global_storage_instance is not None:
        return _global_storage_instance
        
    storage_type = os.getenv("STORAGE", "memory").lower()
    if storage_type == "dynamodb":
        _global_storage_instance = DynamoDBStorage()
    else:
        _global_storage_instance = MemoryStorage()
    return _global_storage_instance
