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
    mock_table_client.upsert_entity.assert_called_once_with(
        entity={
            "PartitionKey": "AnalyticsType",
            "RowKey": "MetricID",
            "total_visitor": 1,
            "visitor_counter": 1,
            "last_updated": mock_datetime.isoformat()
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
        "total_visitor": 5,
        "visitor_counter": 3,
        "last_updated": "2025-09-03T09:00:00.000000"
    }
    mock_table_client.get_entity.return_value = existing_entity
    
    mock_table_service_client.from_connection_string.return_value.get_table_client.return_value = mock_table_client

    mock_datetime = datetime(2025, 9, 3, 11, 0, 0)
    with patch('function_app.datetime') as mock_dt:
        mock_dt.utcnow.return_value = mock_datetime
        mock_dt.fromisoformat.side_effect = datetime.fromisoformat

        response = function_app.getVisitorCount(mock_request)

    assert response.status_code == 200
    mock_table_client.upsert_entity.assert_called_once_with(
        entity={
            "PartitionKey": "AnalyticsType",
            "RowKey": "MetricID",
            "total_visitor": 6,
            "visitor_counter": 4,
            "last_updated": mock_datetime.isoformat()
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
        "total_visitor": 10,
        "visitor_counter": 5,
        "last_updated": "2025-09-02T23:59:59.000000"
    }
    mock_table_client.get_entity.return_value = existing_entity
    
    mock_table_service_client.from_connection_string.return_value.get_table_client.return_value = mock_table_client

    mock_datetime = datetime(2025, 9, 3, 0, 0, 1)
    with patch('function_app.datetime') as mock_dt:
        mock_dt.utcnow.return_value = mock_datetime
        mock_dt.fromisoformat.side_effect = datetime.fromisoformat
        
        response = function_app.getVisitorCount(mock_request)

    assert response.status_code == 200
    mock_table_client.upsert_entity.assert_called_once_with(
        entity={
            "PartitionKey": "AnalyticsType",
            "RowKey": "MetricID",
            "total_visitor": 11,
            "visitor_counter": 1,
            "last_updated": mock_datetime.isoformat()
        },
        mode="replace"
    )


@patch('function_app.os.environ')
@patch('function_app.TableServiceClient')
def test_initial_visit(mock_table_service_client, mock_environ):
    mock_environ.get.return_value = "fake_connection_string"

    mock_table_client = MagicMock()
    mock_table_client.get_entity.side_effect = ResourceNotFoundError("Entity not found.")
    
    mock_table_service_client.from_connection_string.return_value.get_table_client.return_value = mock_table_client
    
    mock_datetime = datetime(2025, 9, 3, 10, 0, 0)
    with patch('function_app.datetime') as mock_dt:
        mock_dt.utcnow.return_value = mock_datetime
        mock_dt.fromisoformat.side_effect = lambda s: datetime.fromisoformat(s.replace("Z", ""))

        req = func.HttpRequest(
            method='GET',
            url='/api/getVisitorCount',
            body=None,
            headers={'Content-Type': 'application/json'}
        )
        
        response = function_app.getVisitorCount(req)

    assert response.status_code == 200
    assert response.get_body() == b'Visitor Counter Updated.'
    
    mock_table_client.upsert_entity.assert_called_once_with(
        entity={
            "PartitionKey": "AnalyticsType",
            "RowKey": "MetricID",
            "total_visitor": 1,
            "visitor_counter": 1,
            "last_updated": mock_datetime.isoformat()
        },
        mode="replace"
    )