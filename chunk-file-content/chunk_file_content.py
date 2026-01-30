"""
Module for saving the chunk file content in S3      
"""

import os
import json
import boto3    
from botocore.exceptions import ClientError,BotoCoreError
import logging

# Initialize logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Get configuration from environment variables

REGION_NAME = os.environ.get("REGION_NAME", "ap-south-1")
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "code-explainability-bucket")

# Initialize s3 client
s3_client = boto3.client("s3", region_name=REGION_NAME)


def lambda_handler(event, context):
    """
      AWS Lambda handler for saving the chunk file content in S3        
    """
    try:
        logger.info("Received event: %s", event)
        logger.info("Received context: %s", context)
        reverse_engg_id = event.get("ReverseEnggID")
        index = event.get("Index")
        file_path = event.get("FilePath")
        chunk_keys = event.get("Chunk_keys")

        logger.info("ReverseEnggID: %s",reverse_engg_id)
        logger.info("Index: %s",index)
        logger.info("FilePath: %s",file_path)
        logger.info("Chunk_keys: %s",chunk_keys)                
        
        #save each chunk to s3
        for chunk in chunk_keys:
            try:
                s3_client.put_object(Bucket=S3_BUCKET_NAME, Key=chunk, Body=chunk)
                logger.info("Saved chunk: %s",chunk)
            except ClientError as e:
                logger.error("Error saving chunk: %s",chunk)
                logger.error("Error: %s",e)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Chunks saved successfully"
            })
        }
    except Exception as e:
        logger.error("Error saving chunks: %s",e)
        return {
            "statusCode": 500,
            "body": json.dumps({
                "message": "Error saving chunks"
            })
        }