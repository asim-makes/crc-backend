import json
import logging
import os
from datetime import datetime

from azure.data.tables import TableServiceClient
import azure.functions as func

# Create a function app instance
app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

def handle_visitor_request(req: func.HttpRequest) -> func.HttpResponse:
    try:
        conn_str = os.environ["CosmosDbConnection"]

        service = TableServiceClient.from_connection_string(conn_str)
        table_client = service.get_table_client(table_name="visitor-counter")

        partition_key = "AnalyticsType"
        row_key = "MetricID"

        try:
            visitor_entity = table_client.get_entity(
                partition_key=partition_key,
                row_key=row_key
            )
            visitors_since_created = visitor_entity.get("visitors_since_created", 0)
            visitors_today = visitor_entity.get("visitors_today", 0)
            last_visited = visitor_entity.get("last_visited", 0)

        except:
            # Initialize if entity doesnot exist.
            visitor_entity = None
            visitors_since_created = 0
            visitors_today = 0
            last_visited = datetime.utcnow()

        # Total visitor since site creation
        visitors_since_created += 1

        # Total visitor today. Needs to be reset everyday.
        today = datetime.utcnow()
        if isinstance(last_visited, str):
            last_visited = datetime.fromisoformat(last_visited.replace("Z", ""))
        if last_visited.date() == today.date():
            new_visitors_today = visitors_today + 1
        else:
            new_visitors_today = 1

        update_entity = {
            "PartitionKey": partition_key,
            "RowKey": row_key,
            "visitors_since_created": visitors_since_created,
            "visitors_today": new_visitors_today,
            "last_visited": datetime.utcnow().isoformat()
        }

        table_client.upsert_entity(entity=update_entity, mode="replace")

        return func.HttpResponse(
            "Visitor Counter Updated.", 
            status_code=200
        )
    
    except Exception as e:
        logging.error(f"An error occured: {e}")
        return func.HttpResponse(
            "An error occured while updating the counter.",
            status_code=500
        )

@app.function_name(name="get_visitor_counter")
@app.route(route="getVisitorCount")
def getVisitorCount(req: func.HttpRequest) -> func.HttpResponse:

    logging.info("Processed a request.")

    return handle_visitor_request(req)
