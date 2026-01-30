import unittest
from unittest.mock import patch, MagicMock
import sys
import json
import os

# Define a real class for ClientError so it can be used in 'except' blocks
class MockClientError(Exception):
    def __init__(self, error_response, operation_name):
        self.response = error_response
        self.operation_name = operation_name
        super().__init__(str(error_response))

# Mock boto3 and botocore before they are imported by the module under test
mock_boto3 = MagicMock()
mock_botocore_exceptions = MagicMock()
mock_botocore_exceptions.ClientError = MockClientError

sys.modules["boto3"] = mock_boto3
sys.modules["botocore"] = MagicMock()
sys.modules["botocore.exceptions"] = mock_botocore_exceptions

# Set dummy environment variables
os.environ["REGION_NAME"] = "us-east-1"
os.environ["S3_BUCKET_NAME"] = "test-bucket"

# Now import the module
import chunk_cleanup

class TestChunkCleanup(unittest.TestCase):

    def setUp(self):
        # Reset the mock before each test
        chunk_cleanup.s3_client.delete_object.reset_mock(side_effect=True, return_value=True)

    def test_lambda_handler_success(self):
        event = {
            "ReverseEnggID": "REQ123",
            "FilePath": "/path/to/file",
            "Chunk_keys": ["chunk1.txt", "chunk2.txt"]
        }
        context = "test-context"
        
        response = chunk_cleanup.lambda_handler(event, context)
        
        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["message"], "Chunks deleted successfully")
        
        # Verify delete_object was called for both chunks
        self.assertEqual(chunk_cleanup.s3_client.delete_object.call_count, 2)
        chunk_cleanup.s3_client.delete_object.assert_any_call(Bucket="test-bucket", Key="chunk1.txt")
        chunk_cleanup.s3_client.delete_object.assert_any_call(Bucket="test-bucket", Key="chunk2.txt")

    def test_lambda_handler_partial_failure(self):
        # Simulate a ClientError for the first chunk
        from botocore.exceptions import ClientError
        error_response = {'Error': {'Code': 'NoSuchKey', 'Message': 'The specified key does not exist.'}}
        chunk_cleanup.s3_client.delete_object.side_effect = [
            ClientError(error_response, 'DeleteObject'),
            None
        ]
        
        event = {
            "Chunk_keys": ["missing_chunk.txt", "existing_chunk.txt"]
        }
        response = chunk_cleanup.lambda_handler(event, None)
        
        # The code catches ClientError and continues, so it should still return 200
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(chunk_cleanup.s3_client.delete_object.call_count, 2)

    def test_lambda_handler_empty_keys(self):
        event = {"Chunk_keys": []}
        response = chunk_cleanup.lambda_handler(event, None)
        
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(chunk_cleanup.s3_client.delete_object.call_count, 0)

    def test_lambda_handler_missing_keys_error(self):
        # If Chunk_keys is missing, the code will raise error when iterating over None
        event = {"ReverseEnggID": "REQ123"}
        response = chunk_cleanup.lambda_handler(event, None)
        
        self.assertEqual(response["statusCode"], 500)
        body = json.loads(response["body"])
        self.assertEqual(body["message"], "Error deleting chunks")

if __name__ == "__main__":
    unittest.main()
