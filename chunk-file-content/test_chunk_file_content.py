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
os.environ["REGION_NAME"] = "ap-south-1"
os.environ["S3_BUCKET_NAME"] = "test-bucket"

# Now import the module
import chunk_file_content

class TestChunkFileContent(unittest.TestCase):

    def setUp(self):
        # Reset the mock before each test
        chunk_file_content.s3_client.put_object.reset_mock(side_effect=True, return_value=True)

    def test_lambda_handler_success(self):
        event = {
            "ReverseEnggID": "REQ123",
            "Index": 1,
            "FilePath": "/path/to/file",
            "Chunk_keys": ["chunk1.txt", "chunk2.txt"]
        }
        context = "test-context"
        
        response = chunk_file_content.lambda_handler(event, context)
        
        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["message"], "Chunks saved successfully")
        
        # Verify put_object was called for both chunks
        self.assertEqual(chunk_file_content.s3_client.put_object.call_count, 2)
        # Note: The original code does s3_client.put_object(..., Body=chunk) where chunk IS the key.
        chunk_file_content.s3_client.put_object.assert_any_call(Bucket="test-bucket", Key="chunk1.txt", Body="chunk1.txt")
        chunk_file_content.s3_client.put_object.assert_any_call(Bucket="test-bucket", Key="chunk2.txt", Body="chunk2.txt")

    def test_lambda_handler_partial_failure(self):
        # Simulate a ClientError for the first chunk
        chunk_file_content.s3_client.put_object.side_effect = [
            MockClientError({'Error': {'Code': 'AccessDenied'}}, 'PutObject'),
            None
        ]
        
        event = {
            "Chunk_keys": ["failed_chunk.txt", "success_chunk.txt"]
        }
        response = chunk_file_content.lambda_handler(event, "test-context")
        
        # The code catches ClientError and continues
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(chunk_file_content.s3_client.put_object.call_count, 2)

    def test_lambda_handler_generic_exception(self):
        # Trigger an exception (e.g., event is None)
        response = chunk_file_content.lambda_handler(None, "test-context")
        
        self.assertEqual(response["statusCode"], 500)
        body = json.loads(response["body"])
        self.assertEqual(body["message"], "Error saving chunks")

if __name__ == "__main__":
    unittest.main()
