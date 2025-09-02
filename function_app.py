import json
import logging
import os
from datetime import datetime

from azure.data.tables import TableServiceClient
import azure.functions as func

# Create a function app instance
app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

@app.function_name(name="get_visitor_counter")
@app.route(route="getVisitorCount")
def getVisitorCount(req: func.HTTPRequest) -> func.HttpResponse:

    logging.info("Processed a request.")

    try:
        # Code for fetching and updating databse
        pass
    except Exception as e:
        logging.error(f"An error occured: {e}")
        return func.HTTPResponse(
            "An error occured while updating the counter.",
            status_code=500
        )