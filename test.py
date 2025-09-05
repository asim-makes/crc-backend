from datetime import datetime
import json
from unittest.mock import MagicMock, patch

import pytest
import azure.functions as func
from azure.core.exceptions import ResourceNotFoundError

import function_app


@pytest.fixture
def mock_request():
    req = func.HttpRequest(
        method="GET",
        url="/api/getVisitorCount",
        body=None,
        headers={
            "Content-Type": "application/json"
        }
    )
    return req


@patch('function_app.os.environ')
@patch('function_app.TableServiceClient')
def test_initial_visit(mock_table_service_client, mock_environ, mock_request):
    """Tests the scenario where the visitor count entity does not exist."""
    
    mock_environ.get.return_value = "fake_connection_string"

    mock_table_client = MagicMock()
    mock_table_client.get_entity.side_effect = ResourceNotFoundError("Entity not found.")
    
    mock_table_service_client.from_connection_string.return_value.get_table_client.return_value = mock_table_client
    
    
    mock_datetime = datetime(2025, 9, 3, 10, 0, 0)
    with patch('function_app.datetime') as mock_dt:
        mock_dt.utcnow.return_value = mock_datetime
        mock_dt.fromisoformat.side_effect = datetime.fromisoformat
        
        
        response = function_app.getVisitorCount(mock_request)

    assert response.status_code == 200
    response_body = json.loads(response.get_body())
    assert response_body["visitorCount"] == 1
    assert response_body["totalVisitors"] == 1
    assert response_body["lastVisited"] == mock_datetime.isoformat()

    mock_table_client.upsert_entity.assert_called_once_with(
        entity={
            "PartitionKey": "AnalyticsType",
            "RowKey": "MetricID",
            "visitors_since_created": 1,
            "visitors_today": 1,
            "last_visited": mock_datetime.isoformat()
        },
        mode="replace"
    )



@patch('function_app.os.environ')
@patch('function_app.TableServiceClient')
def test_same_day_visit(mock_table_service_client, mock_environ, mock_request):
    """Tests a subsequent visit on the same day."""
    mock_environ.get.return_value = "fake_connection_string"
    
    mock_table_client = MagicMock()
    
    existing_entity = {
        "PartitionKey": "AnalyticsType",
        "RowKey": "MetricID",
        "visitors_since_created": 5,
        "visitors_today": 3,
        "last_visited": "2025-09-03T09:00:00"
    }
    mock_table_client.get_entity.return_value = existing_entity
    
    mock_table_service_client.from_connection_string.return_value.get_table_client.return_value = mock_table_client

    mock_datetime = datetime(2025, 9, 3, 11, 0, 0)
    with patch('function_app.datetime') as mock_dt:
        mock_dt.utcnow.return_value = mock_datetime
        mock_dt.fromisoformat.side_effect = datetime.fromisoformat

        response = function_app.getVisitorCount(mock_request)

    assert response.status_code == 200
    response_body = json.loads(response.get_body())
    assert response_body["visitorCount"] == 4
    assert response_body["totalVisitors"] == 6
    assert response_body["lastVisited"] == existing_entity["last_visited"]
    mock_table_client.upsert_entity.assert_called_once_with(
        entity={
            "PartitionKey": "AnalyticsType",
            "RowKey": "MetricID",
            "visitors_since_created": 6,
            "visitors_today": 4,
            "last_visited": mock_datetime.isoformat()
        },
        mode="replace"
    )


@patch('function_app.os.environ')
@patch('function_app.TableServiceClient')
def test_new_day_visit(mock_table_service_client, mock_environ, mock_request):
    """Tests a visit on a new day, which should reset the daily counter."""
    mock_environ.get.return_value = "fake_connection_string"
    
    mock_table_client = MagicMock()
    
    existing_entity = {
        "PartitionKey": "AnalyticsType",
        "RowKey": "MetricID",
        "visitors_since_created": 10,
        "visitors_today": 5,
        "last_visited": "2025-09-02T23:59:59"
    }
    mock_table_client.get_entity.return_value = existing_entity
    
    mock_table_service_client.from_connection_string.return_value.get_table_client.return_value = mock_table_client

    mock_datetime = datetime(2025, 9, 3, 0, 0, 1)
    with patch('function_app.datetime') as mock_dt:
        mock_dt.utcnow.return_value = mock_datetime
        mock_dt.fromisoformat.side_effect = datetime.fromisoformat
        
        response = function_app.getVisitorCount(mock_request)

    assert response.status_code == 200
    response_body = json.loads(response.get_body())
    assert response_body["visitorCount"] == 1
    assert response_body["totalVisitors"] == 11
    assert response_body["lastVisited"] == existing_entity["last_visited"]

    mock_table_client.upsert_entity.assert_called_once_with(
        entity={
            "PartitionKey": "AnalyticsType",
            "RowKey": "MetricID",
            "visitors_since_created": 11,
            "visitors_today": 1,
            "last_visited": mock_datetime.isoformat()
        },
        mode="replace"
    )