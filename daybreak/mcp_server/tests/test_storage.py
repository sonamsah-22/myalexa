"""
Unit tests for storage backends (MemoryStorage & DynamoDBStorage interface compatibility).
"""
import pytest
from unittest.mock import MagicMock, patch
from daybreak.mcp_server.storage import MemoryStorage, DynamoDBStorage, get_storage, DEMO_USER_PK


def test_memory_storage_crud():
    storage = MemoryStorage()
    storage.clear_all()
    
    # Test add event
    ev = storage.add_event(title="Meeting", date="2026-10-04", start_time="09:00", end_time="10:00")
    assert ev["pk"] == DEMO_USER_PK
    assert len(storage.get_events("2026-10-04")) == 1
    
    # Test add task & complete
    t = storage.add_task(title="Write code", duration_min=30)
    assert not t["done"]
    done_t = storage.complete_task("code")
    assert done_t is not None
    assert done_t["done"]
    
    # Test save & get plan
    storage.save_plan(date="2026-10-04", summary="Great plan")
    plan = storage.get_plan("2026-10-04")
    assert plan["summary"] == "Great plan"


@patch("boto3.resource")
def test_dynamodb_storage_interface(mock_boto_resource):
    """Test DynamoDBStorage initialization and query mapping using mocked boto3."""
    mock_table = MagicMock()
    mock_boto_resource.return_value.Table.return_value = mock_table
    
    mock_table.query.return_value = {"Items": []}
    mock_table.get_item.return_value = {}
    
    storage = DynamoDBStorage(table_name="planner_test")
    events = storage.get_events("2026-10-04")
    assert events == []
    mock_table.query.assert_called_once()
