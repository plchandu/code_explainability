import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Add the current directory to sys.path to import authorizer
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Mock environment variables before importing authorizer
with patch.dict('os.environ', {'ISSUER': 'https://cognito-idp.us-east-1.amazonaws.com/us-east-1_test'}):
    import authorizer

class TestAuthorizer(unittest.TestCase):

    def test_generate_policy(self):
        principal_id = "test-user"
        effect = "Allow"
        resource = "arn:aws:execute-api:us-east-1:123456789012:apiId/dev/GET/resource"
        custom_code = 200
        custom_message = "Success"
        error_message = ""

        policy = authorizer.generate_policy(principal_id, effect, resource, custom_code, custom_message, error_message)

        self.assertEqual(policy['principalId'], principal_id)
        self.assertEqual(policy['policyDocument']['Statement'][0]['Effect'], effect)
        self.assertEqual(policy['policyDocument']['Statement'][0]['Resource'], resource)
        self.assertEqual(policy['context']['custom_code'], custom_code)
        self.assertEqual(policy['context']['custom_message'], custom_message)

    @patch('authorizer.requests.get')
    def test_get_public_keys_success(self, mock_get):
        # Mock successful JWKS response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "keys": [
                {"kid": "key-1", "kty": "RSA", "use": "sig", "alg": "RS256", "n": "n-val", "e": "e-val"}
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        keys = authorizer.get_public_keys("key-1")
        self.assertEqual(keys['kid'], "key-1")
        self.assertEqual(keys['alg'], "RS256")

    @patch('authorizer.requests.get')
    def test_get_public_keys_failure(self, mock_get):
        # Mock JWKS response without the requested kid
        mock_response = MagicMock()
        mock_response.json.return_value = {"keys": []}
        mock_get.return_value = mock_response

        with self.assertRaises(ValueError) as cm:
            authorizer.get_public_keys("non-existent-kid")
        self.assertEqual(str(cm.exception), "Public key not found for the given key id")

    @patch('authorizer.jwt.get_unverified_header')
    @patch('authorizer.get_public_keys')
    @patch('authorizer.jwt.decode')
    def test_validate_token_success(self, mock_decode, mock_get_keys, mock_get_header):
        mock_get_header.return_value = {"kid": "key-1"}
        mock_get_keys.return_value = {"kid": "key-1"}
        mock_decode.return_value = {"sub": "user-123"}

        payload = authorizer.validate_token("valid.token.here")
        self.assertEqual(payload['sub'], "user-123")
        mock_decode.assert_called_once()

    @patch('authorizer.validate_token')
    def test_lambda_handler_allow(self, mock_validate):
        event = {
            "headers": {"Authorization": "Bearer valid_token"},
            "methodArn": "arn:aws:execute-api:resource"
        }
        mock_validate.return_value = {"sub": "user-123"}

        response = authorizer.lambda_handler(event, None)
        self.assertEqual(response['policyDocument']['Statement'][0]['Effect'], "Allow")

    @patch('authorizer.validate_token')
    def test_lambda_handler_deny_missing_token(self, mock_validate):
        event = {
            "headers": {}, # Missing Authorization header
            "methodArn": "arn:aws:execute-api:resource"
        }

        response = authorizer.lambda_handler(event, None)
        self.assertEqual(response['policyDocument']['Statement'][0]['Effect'], "Deny")
        self.assertEqual(response['context']['custom_code'], 401)

    @patch('authorizer.validate_token')
    def test_lambda_handler_deny_invalid_token(self, mock_validate):
        event = {
            "headers": {"Authorization": "Bearer invalid_token"},
            "methodArn": "arn:aws:execute-api:resource"
        }
        mock_validate.side_effect = ValueError("Invalid token")

        response = authorizer.lambda_handler(event, None)
        self.assertEqual(response['policyDocument']['Statement'][0]['Effect'], "Deny")
        self.assertEqual(response['context']['custom_code'], 401)

if __name__ == '__main__':
    unittest.main()
