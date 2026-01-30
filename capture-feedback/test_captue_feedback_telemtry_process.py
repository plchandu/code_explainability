import unittest
from unittest.mock import patch, MagicMock
import sys
import json
import os

# Mock boto3 and botocore before they are imported by the module under test
mock_boto3 = MagicMock()
mock_botocore = MagicMock()
sys.modules["boto3"] = mock_boto3
sys.modules["botocore"] = mock_botocore
sys.modules["botocore.exceptions"] = mock_botocore.exceptions

# Set dummy environment variables
os.environ["TELEMETRY_LAMBDA_NAME"] = "test-telemetry"
os.environ["DYNAMO_TABLE_REQUEST"] = "test-table"
os.environ["LAMBDA_NAME"] = "test-lambda"

# Now import the module
from capture_feedback_telemetry_process import (
    calculate_response,
    prepare_telemetry_payload,
    process_event_and_call_telemetry_lambda
)

class TestTelemetryProcess(unittest.TestCase):

    def test_calculate_response_success(self):
        feedback = [
            {"Option": "Yes"},
            {"Option": "No"},
            {"Option": "yes"}
        ]
        total, positive, negative = calculate_response(feedback)
        self.assertEqual(total, 3)
        self.assertEqual(positive, 2)
        self.assertEqual(negative, 1)

    def test_calculate_response_empty(self):
        total, positive, negative = calculate_response([])
        self.assertEqual(total, 0)
        self.assertEqual(positive, 0)
        self.assertEqual(negative, 0)

    def test_prepare_telemetry_payload_success(self):
        event = {"headers": {"authorization": "token"}}
        custom_props = {
            "feedback_array": [{"Option": "Yes"}],
            "userInfo": {"UserLanId": "user1"},
            "applicationGearID": "gear1",
            "ReverseEnggID": "corr1"
        }
        payload = prepare_telemetry_payload(event, "test_event", "desc", custom_props, is_error=False)
        
        self.assertIn("headers", payload)
        self.assertIn("body", payload)
        body = json.loads(payload["body"])
        self.assertEqual(body["applicationGearID "], "gear1")
        self.assertEqual(body["correlationID"], "corr1")
        event_data = body["events"][0]
        self.assertEqual(event_data["eventName"], "test_event")
        self.assertEqual(event_data["eventProperties"]["status"], "success")
        self.assertEqual(event_data["eventProperties"]["total_responses"], 1)

    def test_prepare_telemetry_payload_error(self):
        event = {"headers": {}}
        custom_props = {
            "feedback_array": [],
            "error": "some_error"
        }
        payload = prepare_telemetry_payload(event, "test_error", "desc", custom_props, is_error=True)
        body = json.loads(payload["body"])
        self.assertEqual(body["events"][0]["eventProperties"]["status"], "failed")
        self.assertEqual(body["events"][0]["eventProperties"]["error"], "some_error")

    @patch("capture_feedback_telemetry_process.invoke_telemetry_lambda")
    def test_process_event_success(self, mock_invoke):
        mock_invoke.return_value = {"status": "ok"}
        event = {}
        custom_props = {"feedback_array": []}
        response = process_event_and_call_telemetry_lambda(event, "name", "desc", custom_props)
        self.assertEqual(response, {"status": "ok"})
        mock_invoke.assert_called_once()

if __name__ == "__main__":
    unittest.main()
