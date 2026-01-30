# Debugging Guide for Authorizer

This guide outlines how to debug the `authorizer.py` Lambda function.

## 1. Local Debugging (The Easiest Way)

### Run Unit Tests
We have a comprehensive test suite in `test_authorizer.py` that mocks external calls. This is the fastest way to check logic changes.
```bash
python3 authorizer/test_authorizer.py
```

### Manual Script Execution
You can simulate a Lambda execution by adding a temporary block at the end of `authorizer.py` or creating a small runner script:
```python
# debug_runner.py
from authorizer import lambda_handler
import os

os.environ['ISSUER'] = 'https://cognito-idp.us-east-1.amazonaws.com/your-user-pool-id'

mock_event = {
    "headers": {
        "Authorization": "Bearer YOUR_JWT_HERE"
    },
    "methodArn": "arn:aws:execute-api:..."
}

print(lambda_handler(mock_event, None))
```

---

## 2. Cloud Debugging (AWS CloudWatch)

The code uses the `logging` module. When running in AWS:
1. Go to the **Lambda Console**.
2. Click on the **Monitor** tab.
3. Click **View CloudWatch Logs**.
4. Look for `INFO` or `ERROR` messages.

### Critical Logs to Watch:
- `Event: {...}`: See exactly what API Gateway is sending.
- `Fetching public keys from JWKS`: Check if the Lambda can reach the Internet and the Cognito URL.
- `Generated policy: {...}`: Verify the final JSON format returned to API Gateway.

---

## 3. Common Issues

### 1. `IndexError` on Token Extraction
**Symptom**: Authorizer fails before logging anything useful.
**Cause**: The `Authorization` header is missing or doesn't have a space (e.g., just "token" instead of "Bearer token").
**Fix**: Ensure your client sends `Bearer <token>`.

### 2. `JWKS` Fetch Failure
**Symptom**: `Failed to fetch public keys from JWKS`.
**Cause**:
- Incorrect `ISSUER` URL.
- Lambda is in a VPC without a NAT Gateway (no internet access).
**Fix**: Verify the `ISSUER` environment variable in the Lambda console.

### 3. `kid` Mismatch
**Symptom**: `Public key not found for the given key id`.
**Cause**: The JWT was issued by a different User Pool or Issuer than the one configured in the Lambda.
**Fix**: Compare the `kid` in the log with the keys listed at `https://cognito-idp.<region>.amazonaws.com/<user-pool-id>/.well-known/jwks.json`.

---

## 4. Useful Tools
- **[jwt.io](https://jwt.io)**: Paste your token here to see the `header` (check `kid`) and `payload` (check `exp` and `iss`).
- **Postman/Insomnia**: Use these to test your API Gateway endpoint and see the `401` or `403` responses.
