"""
AWS Lambda function for cleaning up outdated Bedrock knowledge bases and associated resources.

This modules handles the automated deletion of knowledge bases, data sources, and vector tables
that have not been used for a specified period of time. It supports both single-item deletion
and batch deletion of multiple items to avoid API GATEWAY timeout.

"""

import json
import os
import boto3
from botocore.exceptions import ClientError
import time
import uuid
import logging
from http import HTTPStatus
from datetimr import datetime,timedelta,timezone
from typing import Dict, List, Optional
import psycopg2

# Configure Logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)
KBS_PER_BATCH = int(os.getenv("KBS_PER_BATCH", 10))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", 3))
RETRY_DELAY = int(os.getenv("RETRY_DELAY", 5))
DEFAULT_DAYS_THRESHOLD = int(os.getenv("DEFAULT_DAYS_THRESHOLD", 30))
DELAY_BETWEEN_KBS = int(os.getenv("DELAY_BETWEEN_KBS", 5))
KB_PREFIX = os.getenv("KB_PREFIX", "kb_")
DYNAMODB_TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME", "cleanup-status-checker")
REGION = os.getenv("REGION", "ap-south-1")

class DateTimeEncoder(json.JSONEncoder):
    """
    Custom JSON encoder to serialize datetime objects.
    """
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

class BedrockDBAgent:
    """
    Agent to interact with  Amazon Bedrock Knowledge base.
    This class provides methods for managing knowledge bases, data sources, and their associated metadata in DynamoDB.
    """
    def __init__(self,region_name - REGION):
        self.bedrock_client = boto3.client("bedrock", region_name=region_name)
        self.dynamodb_client = boto3.client("dynamodb", region_name=region_name)
        self.dynamodb_table = DYNAMODB_TABLE_NAME

    def list_knowledge_bases(self):
        """
        List all knowledge bases in Bedrock.
        """
        knowledge_bases = []
        next_token = None
        try:
            while True:
                response = self.bedrock_client.list_knowledge_bases(
                    NextToken=next_token
                )
                knowledge_bases.extend(response.get("KnowledgeBases", []))
                next_token = response.get("NextToken")
                if not next_token:
                    break
            return knowledge_bases
        except ClientError as e:
            logger.error("Error listing knowledge bases: %s", e)
            return []

    def get_kb_and_ds_id(self,ReverseEnggID):
        """
        Get knowledge base and data source IDs for reverse engineering ID.
        """
        try:
            response = self.dynamodb_client.get_item(
                TableName=self.dynamodb_table,
                Key={
                    "ReverseEnggID": {"S": ReverseEnggID}
                }
            )
            item = response.get("Item")
            if item:
                return item.get("KBID").get("S"), item.get("DSID").get("S")
            return None, None
        except ClientError as e:
            logger.error("Error getting knowledge base and data source IDs: %s", e)
            return None, None
        
    def get_cleanup_status(self,ReverseEnggID):
        """
        Get cleanup status for reverse engineering ID.
        """
        try:
            response = self.dynamodb_client.get_item(
                TableName=self.dynamodb_table,
                Key={
                    "ReverseEnggID": {"S": ReverseEnggID}
                }
            )
            item = response.get("Item")
            if item:
                return item.get("CleanupStatus").get("S")
            return None
        except ClientError as e:
            logger.error("Error getting cleanup status: %s", e)
            return None
        
    def update_cleanup_status(self,ReverseEnggID,status):
        """
        Update cleanup status for reverse engineering ID.
        """
        try:
            self.dynamodb_client.update_item(
                TableName=self.dynamodb_table,
                Key={
                    "ReverseEnggID": {"S": ReverseEnggID}
                },
                UpdateExpression="set CleanupStatus = :status",
                ExpressionAttributeValues={
                    ":status": {"S": status}
                }
            )
        except ClientError as e:
            logger.error("Error updating cleanup status: %s", e)

    def delete_ds(self,kb_id, ds_id):
        """
        Delete data source for knowledge base ID.
        """
        try:
            self.bedrock_client.delete_data_source(
                KnowledgeBaseId=kb_id,
                DataSourceId=ds_id
            )
        except ClientError as e:
            logger.error("Error deleting data source: %s", e)
        
    def delete_kb(self,kb_id):
        """
        Delete knowledge base for knowledge base ID.
        """
        try:
            self.bedrock_client.delete_knowledge_base(
                KnowledgeBaseId=kb_id
            )
        except ClientError as e:
            logger.error("Error deleting knowledge base: %s", e)

    def remove_kb_and_ds_id(self,ReverseEnggID):
        """
        Remove knowledge base and data source IDs for reverse engineering ID from DynamoDB  table  .
        """
        try:
            self.dynamodb_client.delete_item(
                TableName=self.dynamodb_table,
                Key={
                    "ReverseEnggID": {"S": ReverseEnggID}
                }
            )
        except ClientError as e:
            logger.error("Error removing knowledge base and data source IDs: %s", e)

    def update_cleanup_status(self,ReverseEnggID,status,comment=None):
        """
        Update cleanup status for reverse engineering ID.
        """
        try:
            self.dynamodb_client.update_item(
                TableName=self.dynamodb_table,
                Key={
                    "ReverseEnggID": {"S": ReverseEnggID}
                },
                UpdateExpression="set CleanupStatus = :status, CleanupComment = :comment if CleanupComment is null ",
                ExpressionAttributeValues={
                    ":status": {"S": status},
                    ":comment": {"S": comment}
                }
            )
        except ClientError as e:
            logger.error("Error updating cleanup status: %s", e)
        
    def check_and_retry_kb_deletion(self,kb_id,max_retries=3,delay=DELAY_BETWEEN_KBS,   ReverseEnggID):
        """
        Check and retry knowledge base deletion.
        """
        try:
            for i in range(max_retries):
                try:
                    self.delete_kb(kb_id)
                    return True
                except ClientError as e:
                    logger.error("Error deleting knowledge base: %s", e)
                    time.sleep(delay)
            return False
        except ClientError as e:
            logger.error("Error checking and retrying knowledge base deletion: %s", e)
            return False
        
class VectorTableDeleter:
    """
    Class to delete vector table.
    """
    def __init__(self):
        self.database_name = DATABASE_NAME
        self.SECRET_NAME = DATABASE_SECRET_NAME
        self.region = REGION
      
    def get_secrets(self):
        """
        Get secrets from AWS Secrets Manager.
        """
        try:
            secrets_manager_client = boto3.client("secretsmanager", region_name=self.region)
            secret_value = secrets_manager_client.get_secret_value(SecretId=self.SECRET_NAME)
            return json.loads(secret_value["SecretString"])
        except ClientError as e:
            logger.error("Error getting secrets: %s", e)
            return None
        
    def delete_vector_table(self,ReverseEnggID):
        """
        Delete vector table.
        """
        try:
            secrets = self.get_secrets()
            if not secrets:
                logger.error("Error getting secrets")
                return False
            
            host = secrets.get("host")
            port = secrets.get("port")
            user = secrets.get("user")
            password = secrets.get("password")
            
            conn = psycopg2.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                dbname=self.database_name
            )
            cursor = conn.cursor()
            cursor.execute(f"DROP TABLE IF EXISTS {ReverseEnggID}")
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            logger.error("Error deleting vector table: %s", e)
            return False

    def is_kb_older_than_threshold(updated_at: datetime,days:int)-> bool:
        """
        Check if knowledge base is older than threshold.
        """
        try:
            secrets = self.get_secrets()
            if not secrets:
                logger.error("Error getting secrets")
                return False
            
            host = secrets.get("host")
            port = secrets.get("port")
            user = secrets.get("user")
            password = secrets.get("password")
            
            conn = psycopg2.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                dbname=self.database_name
            )
            cursor = conn.cursor()
            cursor.execute(f"SELECT created_at FROM {ReverseEnggID}")
            result = cursor.fetchone()
            if not result:
                logger.error("Error getting knowledge base creation time")
                return False
            
            created_at = result[0]
            threshold = datetime.now() - timedelta(days=days)
            return created_at < threshold
        except Exception as e:
            logger.error("Error checking if knowledge base is older than threshold: %s", e)
            return False
        
    def extract_re_id(kb_name : str)-> str:
        """
        Extract reverse engineering ID from knowledge base ID.
        """
        try:
            if kb_name.startswith("kb_"):
                return kb_name[3:]
            else:
                return kb_name
        except Exception as e:
            logger.error("Error extracting reverse engineering ID: %s", e)
            return None 

    def find_outdated_kbs(self,days_threshold: int)-> list:
        """
        Find outdated knowledge bases.
        """
        try:
            secrets = self.get_secrets()
            if not secrets:
                logger.error("Error getting secrets")
                return []
            
            host = secrets.get("host")
            port = secrets.get("port")
            user = secrets.get("user")
            password = secrets.get("password")
            
            conn = psycopg2.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                dbname=self.database_name
            )
            cursor = conn.cursor()
            cursor.execute(f"SELECT kb_name FROM {self.dynamodb_table}")
            result = cursor.fetchall()
            if not result:
                logger.error("Error getting knowledge base names")
                return []
            
            outdated_kbs = []
            for kb_name in result:
                if self.is_kb_older_than_threshold(kb_name,days_threshold):
                    outdated_kbs.append(kb_name)
            return outdated_kbs
        except Exception as e:
            logger.error("Error finding outdated knowledge bases: %s", e)
            return []   

    def cleanup(self,days_threshold: int)-> list:
        """
        Cleanup knowledge bases.
        """
        try:
            outdated_kbs = self.find_outdated_kbs(days_threshold)
            for kb_name in outdated_kbs:
                self.delete_kb(kb_name)
            return outdated_kbs
        except Exception as e:
            logger.error("Error cleaning up knowledge bases: %s", e)
            return []   

    def process_kb_batch_asynchronously(self, kb_batch: list,start_index,days_threshold,job_id):
        """
        Process knowledge base batch asynchronously.
        """
        lambda_client = boto3.client("lambda", region_name=self.region)
        for i in range(0, len(kb_batch), self.batch_size):
            batch = kb_batch[i:i + self.batch_size]
            payload = {
                "kb_batch": batch,
                "start_index": i,
                "days_threshold": days_threshold,
                "job_id": job_id
            }
            lambda_client.invoke(
                FunctionName="cleanup-status-checker",
                InvocationType="Event",
                Payload=json.dumps(payload)
            )
    def lambda_handler(event,context):
        """
        Lambda handler function to clean up Bedrock knowledge base.
        """
        try:
            logger.info("Lambda handler function to clean up Bedrock knowledge base.")
            bedrock_agent=BedRockKBAgent()
            vector_deleter=VectorTableDeleter()
            if "kb_batch" in event:
                kb_batch=event["kb_batch"]
                start_index=event["start_index"]
                days_threshold=event["days_threshold"]
                job_id=event["job_id"]
                for kb_name in kb_batch:
                    re_id=bedrock_agent.extract_re_id(kb_name)
                    vector_deleter.delete_vector_table(re_id)   


    def _handle_async_process(self,event,bedrock_agent,vector_deleter):
        kbs_to_process=bedrock_agent.find_outdated_kbs(days_threshold)
        current_index=event["start_index"]
        days_threshold=event["days_threshold"]
        job_id=event["job_id"]
        
        logger.info(f"Processing {len(kbs_to_process)} knowledge bases starting from index {current_index}")
        end_index=min(current_index+self.batch_size,len(kbs_to_process))
        batch_result={"success":[],"failed":[]}
        for i in range(current_index,end_index):
            kb_name=kbs_to_process[i]
            re_id=bedrock_agent.extract_re_id(kb_name)
            if vector_deleter.delete_vector_table(re_id):
                batch_result["success"].append(kb_name)
            else:
                batch_result["failed"].append(kb_name)
        logger.info(f"Batch result: {batch_result}")
        if end_index<len(kbs_to_process):
            self.process_kb_batch_asynchronously(kbs_to_process,end_index,days_threshold,job_id)
        else:
            logger.info(f"All knowledge bases processed")


    def _handle_single_kb_cleanup(self,kb_name,bedrock_agent,vector_deleter):
        re_id=bedrock_agent.extract_re_id(kb_name)
        if vector_deleter.delete_vector_table(re_id):
            return True
        else:
            return False    

    def _handle_bulk_cleanup(self,kb_batch,bedrock_agent,vector_deleter):
        batch_result={"success":[],"failed":[]}
        for kb_name in kb_batch:
            re_id=bedrock_agent.extract_re_id(kb_name)
            if vector_deleter.delete_vector_table(re_id):
                batch_result["success"].append(kb_name)
            else:
                batch_result["failed"].append(kb_name)
        logger.info(f"Batch result: {batch_result}")
        return batch_result 

    def _serialize_kb_batch(self,kb_batch):
        return [kb.replace("kb_","") for kb in kb_batch]

    def _serialize_re_id_batch(self,re_id_batch):
        return ["kb_"+re_id for re_id in re_id_batch]

    def _accepted_response(count,job_id,days_threshold,outdated_kbs):
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": f"Accepted {count} knowledge bases for cleanup",
                "job_id": job_id,
                "days_threshold": days_threshold,
                "outdated_kbs": outdated_kbs
            })
        }

    def _failed_async_start_response():
        return {
            "statusCode": 500,
            "body": json.dumps({
                "message": "Failed to start async process"
            })
        }  

    def _no_kbs_to_cleanup_response():
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "No knowledge bases to cleanup"
            })
        }   

    def _internal_error_response():
        return {
            "statusCode": 500,
            "body": json.dumps({
                "message": "Internal error"
            })
        }       

    def _success_response(message):
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": message
            })
        }   
        
    def _failed_response(message):
        return {
            "statusCode": 500,
            "body": json.dumps({
                "message": message
            })
        }       
        
