import json
import logging
import os
import boto3
import decimal
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Tuple
from capture_feedback_telemetry_process import process_event_and_call_telemetry_lambda, send_error_telemetry

# Initialize logging for CloudWatch visibility
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# --- Configuration & Environment Validation ---
# These variables are required for the module to function correctly.
DYNAMO_TABLE = os.getenv("DYNAMO_TABLE_REPO_REQUEST") 
LAMBDA_NAME = os.getenv("LAMBDA_NAME")  

# Initialize AWS clients
dynamodb = boto3.resource("dynamodb")
repo_table = dynamodb.Table(DYNAMO_TABLE) if DYNAMO_TABLE else None

class DecimalEncoder(json.JSONEncoder):
    """Helper class to convert a DynamoDB item to JSON."""
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

def get_current_time()-> str:
    '''
    Returns the current time in EST
    '''
    utc_time = datetime.now(timezone.utc)
    est_time = utc_time + timedelta(hours=5, minutes=30)
    return est_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")   

def build_response(status_code: int, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    '''
    Builds a standardized response dictionary for API Gateway.
    
    Args:
        status_code (int): HTTP status code.
        body (Optional[Dict[str, Any]]): Data payload to be stringified.
    
    Returns:
        Dict[str, Any]: Standardized response dictionary.
    '''
    response = {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(body, cls=DecimalEncoder) if body else ""
    }
    return response

def get_feedback_data(event: Dict[str, Any]) -> Dict[str, Any]:
    '''
    Extracts feedback data from the event.
    
    Args:
        event (Dict[str, Any]): The Lambda event.
    
    Returns:
        Dict[str, Any]: Feedback data.
    '''
    try:
        feedback_data = event.get("body", {})
        return feedback_data
    except Exception as e:
        logger.error(f"Failed to extract feedback data: {e}")
        raise

def fetch_user_details(ReverseEnggID_id: str) -> Optional[Dict[str, Any]]:
    '''
    Fetches user details from the DynamoDB table.
    
    Args:
            ReverseEnggID_id (str): The ReverseEnggID.
    
    Returns:
        Optional[Dict[str, Any]]: User details.
    '''
    try:
        response = repo_table.get_item(Key={"ReverseEnggID": ReverseEnggID_id})
        logger.warning(f"User details: {response}")
        return response.get("Item", {})
    except Exception as e:
        logger.error(f"Failed to fetch user details: {e}")
        raise

def update_feedback_in_dynamodb(ReverseEnggID_id: str, feedback_data: Dict[str, Any]) -> None:
    '''
    Updates the feedback in the DynamoDB table.
    
    Args:
        ReverseEnggID_id (str): The ReverseEnggID.
        feedback_data (Dict[str, Any]): The feedback data.
    
    Returns:
        None
    '''
    try:
        repo_table.update_item(
            Key={"ReverseEnggID": ReverseEnggID_id},
            UpdateExpression="SET Feedback = :feedback",
            ExpressionAttributeValues={
                ":feedback": feedback_data
            }
        )
        logger.info(f"Feedback updated successfully for ReverseEnggID: {ReverseEnggID_id}")
    except Exception as e:
        logger.error(f"Failed to update feedback: {e}")
        raise

def prepare_telemetry_properties(feedback_data  : Dict[str, Any], user_details: Dict[str, Any]) -> Dict[str, Any]:
    '''
    Prepares the telemetry properties.
    
    Args:
        feedback_data (Dict[str, Any]): The feedback data.
        user_details (Dict[str, Any]): The user details.
    
    Returns:
        Dict[str, Any]: The telemetry properties.
    '''
    try:
        telemetry_properties = {
            "user_info": {
                "userLanid": user_details.get("UserLanId", ""),
                "userEmailId": user_details.get("UserEmailId", ""),
                "first_name": user_details.get("FirstName", ""),
                "last_name": user_details.get("LastName", "")
            },
            "thumbs_value": feedback_data.get("thumbs_value", 0),
            "total_responses": feedback_data.get("total_responses", 0),
            "positive_responses": feedback_data.get("positive_responses", 0),
            "negative_responses": feedback_data.get("negative_responses", 0),
            "lambda": LAMBDA_NAME,
            "feedback": feedback_data.get("feedback", []),
            "status": "failed" if feedback_data.get("status", "") == "failed" else "success"
        }
        logger.info(f"Telemetry properties prepared successfully: {telemetry_properties}")
        return telemetry_properties
    except Exception as e:
        logger.error(f"Failed to prepare telemetry properties: {e}")
        raise
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main entry point for the Lambda function.
    Processes feedback, updates DynamoDB, and sends telemetry.
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # 1. Extract data from Request
        feedback_data = get_feedback_data(event)
        reverse_engg_id = feedback_data.get("ReverseEnggID", "")
        
        # 2. Fetch additional context (user info) from DB
        user_details = fetch_user_details(reverse_engg_id)
        
        # 3. Update the item with feedback
        update_feedback_in_dynamodb(reverse_engg_id, feedback_data)
        
        # 4. Prepare metadata for telemetry
        telemetry_properties = prepare_telemetry_properties(feedback_data, user_details or {})
        
        # 5. Call Telemetry service (Success)
        process_event_and_call_telemetry_lambda(
            event, 
            "feedback_capture_processed", 
            "Feedback successfully captured and stored", 
            telemetry_properties
        )
        
        return build_response(200, {"message": "Feedback processed successfully"})
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to process feedback: {error_msg}")
        
        # Call Telemetry service (Error)
        send_error_telemetry(
            event, 
            "feedback_capture_failed", 
            f"Error processing feedback: {error_msg}", 
            {"error": error_msg}
        )
        
        return build_response(500, {"message": "Failed to process feedback", "error": error_msg})
    