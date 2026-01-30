'''
Module for processing feedback telemetry and invoking the telemetry Lambda function.
This module calculates feedback statistics (positive/negative) and prepares a standardized 
payload for auditing and monitoring via a downstream telemetry service.
'''

import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
import os
import json
import boto3
from botocore.exceptions import ClientError


# Initialize logging for CloudWatch visibility
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# --- Configuration & Environment Validation ---
# These variables are required for the module to function correctly.
try:
    TELEMETRY_LAMBDA_NAME = os.getenv("TELEMETRY_LAMBDA_NAME") 
    DYNAMO_TABLE_REQUEST = os.getenv("DYNAMO_TABLE_REQUEST") 
    LAMBDA_NAME = os.getenv("LAMBDA_NAME")  
    if not TELEMETRY_LAMBDA_NAME:
        raise ValueError("TELEMETRY_LAMBDA_NAME is not set")
    if not DYNAMO_TABLE_REQUEST:
        raise ValueError("DYNAMO_TABLE_REQUEST is not set")
    if not LAMBDA_NAME:
        raise ValueError("LAMBDA_NAME is not set")
except ValueError as e:
    logger.error(f"Missing required environment variable: {e}")
    raise
# Initalize Lambda client
lambda_client = boto3.client("lambda")

def validate_environment_variables():
    """Validate environment variables"""
    if not TELEMETRY_LAMBDA_NAME:
        raise ValueError("TELEMETRY_LAMBDA_NAME is not set")
    if not DYNAMO_TABLE_REQUEST:
        raise ValueError("DYNAMO_TABLE_REQUEST is not set")
    if not LAMBDA_NAME:
        raise ValueError("LAMBDA_NAME is not set")
    logger.info("All environment variables are set")    

def initialize():
    """Initialize the module"""
    try:
        validate_environment_variables()
        logger.info("Module initialized successfully")  
    except ValueError as e:
        logger.error(f"Failed to initialize module: {e}")
        raise

initialize()

def calculate_response(feedback_array: List[Dict[str, Any]]) -> Tuple[int, int, int]:    
    """
    Calculates statistics from an array of feedback items.
    
    Args:
        feedback_array (List[Dict[str, Any]]): A list of dictionaries, where each dict 
                                               is expected to have an 'Option' key (e.g., 'yes' or 'no').
    
    Returns:
        Tuple[int, int, int]: (total_count, positive_count, negative_count)
    
    Example input: [{"Option": "yes"}, {"Option": "no"}, {"Option": "yes"}]
    Example output: (3, 2, 1)
    """
    try:
        if not feedback_array:
            logger.error("No feedback provided")
            return 0,0,0
        
        total_responses = len(feedback_array)
        positive_responses = sum(1 for item in feedback_array if isinstance(item,dict) and item.get("Option",'').lower() == "yes")
        negative_responses = sum(1 for item in feedback_array if isinstance(item,dict) and item.get("Option",'').lower() == "no")
        
        response = {
            "feedback_array": feedback_array,
            "response": "success",
            "timestamp": datetime.now().isoformat()
        }
        logger.info(f"calculte responses - Total: {total_responses}, Positive: {positive_responses}, Negative: {negative_responses}")
        return total_responses,positive_responses,negative_responses
    except ValueError as e:
        logger.error(f"Failed to calculate response: {e}")
        raise

def prepare_telemetry_payload(event: Dict[str, Any], event_name: str, event_description: str, custom_properties: Dict[str, Any], is_error: bool = False) -> Dict[str, Any]:
    """
    Constructs the final payload structure required by the telemetry Lambda.
    
    Args:
        event (Dict[str, Any]): The original Lambda event (used for headers).
        event_name (str): Identifier for the event (e.g., 'feedback_submitted').
        event_description (str): Human-readable description of what happened.
        custom_properties (Dict[str, Any]): Metadata including user info, feedback data, and IDs.
        is_error (bool): Flag indicating if this is an error telemetry event.
    
    Returns:
        Dict[str, Any]: A dictionary containing headers and a JSON-stringified body.
    """
    event_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    feedback_array = custom_properties.get("feedback_array", [])
    logger.info(f"Feedback array: {feedback_array}")
    total_responses, positive_responses, negative_responses = calculate_response(feedback_array)
    event_properties = {
        "user_info": {
            "userLanid": custom_properties.get('userInfo', {}).get('UserLanId', ''),
            "userEmailId": custom_properties.get('userInfo', {}).get('UserEmailId', ''),
            "first_name": custom_properties.get('userInfo', {}).get('FirstName', ''),
            "last_name": custom_properties.get('userInfo', {}).get('LastName', '')
        },
        "thumbs_value": custom_properties.get("thumbs_value", 0),
        "total_responses": total_responses,
        "positive_responses": positive_responses,
        "negative_responses": negative_responses,
        "lambda": LAMBDA_NAME,
        "feedback": feedback_array,
        "status": "failed" if is_error else "success"
    }

    if is_error and "error" in custom_properties:
        event_properties['error'] = custom_properties['error']

    body_data = {
        "aiSvc": "Code Explainability",
        "appVersion": "1.0.0",
        "eventSchemaVersion": "1.0",
        "applicationGearID ": custom_properties.get('applicationGearID', ''),
        "correlationID": custom_properties.get('ReverseEnggID', ''),
        "timestamp": timestamp,
        "events": [
            {
                "eventID": event_id,
                "eventName": event_name,
                "eventDescription": event_description,
                "eventProperties": event_properties
            }
        ]
    }
    logger.info(f"Telemetry payload prepared successfully: {body_data}")
    return {
        "headers": {
            "authorization": event.get('headers', {}).get('authorization', ''),
            "Content-Type": "application/json"
        },
        "body": json.dumps(body_data)
    }
        
def invoke_telemetry_lambda(payload: Dict[str, Any]) -> Dict[str, Any]:  
    """
    Synchronously invokes the telemetry Lambda function with the prepared payload.
    """
    try:
        logger.info(f"Invoking telemetry Lambda: {TELEMETRY_LAMBDA_NAME}")
        response = lambda_client.invoke(
            FunctionName=TELEMETRY_LAMBDA_NAME,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        logger.info(f"Telemetry Lambda response: {response}")
        response.payload = json.loads(response.payload.read())
        return response.payload
    except ClientError as e:
        logger.error(f"Failed to invoke telemetry Lambda: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to invoke telemetry Lambda: {e}")
        raise   
def process_event_and_call_telemetry_lambda(event: Dict[str, Any], event_name: str, event_description: str, custom_properties: Dict[str, Any], is_error: bool = False) -> Dict[str, Any]:
    """
    High-level handler to process an event and trigger the telemetry flow.
    """
    try:
        logger.info(f"Processing event and calling telemetry Lambda: {event_name}")
        payload = prepare_telemetry_payload(event, event_name, event_description, custom_properties, is_error)
        response = invoke_telemetry_lambda(payload)
        return response
    except Exception as e:
        logger.error(f"Failed to process event and call telemetry Lambda: {e}")
        raise

def send_error_telemetry(event: Dict[str, Any], event_name: str, event_description: str, custom_properties: Dict[str, Any]) -> Dict[str, Any]:
    """Send error telemetry"""
    try:
        logger.info(f"Sending error telemetry: {event_name}")
        payload = prepare_telemetry_payload(event, event_name, event_description, custom_properties, is_error=True)
        response = invoke_telemetry_lambda(payload)
        return response
    except Exception as e:
        logger.error(f"Failed to send error telemetry: {e}")
        raise