"""
Module for cleaning up temporary file chunks in S3.
This Lambda function is typically triggered after file processing is complete 
to remove intermediate parts/chunks stored in S3.
"""

import json
import logging
import os
import boto3
from botocore.exceptions import ClientError 

# Initialize logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Get configuration from environment variables
REGION_NAME = os.environ.get("REGION_NAME", "ap-south-1")
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "code-explainability-bucket")

#initialize s3 client
s3_client = boto3.client("s3", region_name=REGION_NAME) 

def lambda_handler(event, context):
    """
    Lambda handler to clean up chunks in S3.
    
    Sample Input (event):
    {
        "ReverseEnggID": "REQ-12345",
        "FilePath": "uploads/source_code.zip",
        "Chunk_keys": ["chunks/part1.txt", "chunks/part2.txt", "chunks/part3.txt"]
    }
    
    Args:
        event (dict): Contains the S3 keys of the chunks to be deleted.
        context (object): Lambda context object.
    
    Returns:
        dict: Success or failure status with a message.
    """
    try:
        logger.info("Received context: %s", context)
        reverse_engg_id = event.get("ReverseEnggID")
        file_path = event.get("FilePath")
        chunk_keys = event.get("Chunk_keys")

        logger.info("ReverseEnggID: %s",reverse_engg_id)
        logger.info("FilePath: %s",file_path)
        logger.info("Chunk_keys: %s",chunk_keys)                
        
        #delete each chunk from s3
        for chunk in chunk_keys:
            try:
                s3_client.delete_object(Bucket=S3_BUCKET_NAME, Key=chunk)
                logger.info("Deleted chunk: %s",chunk)
            except ClientError as e:
                logger.error("Error deleting chunk: %s",chunk)
                logger.error("Error: %s",e)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Chunks deleted successfully"
            })
        }
    except Exception as e:
        logger.error("Error deleting chunks: %s",e)
        return {
            "statusCode": 500,
            "body": json.dumps({
                "message": "Error deleting chunks"
            })
        }
                
            