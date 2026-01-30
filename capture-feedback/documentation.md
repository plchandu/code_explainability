# Capture Feedback - Code Documentation

This document provides a detailed explanation of the `capture_feedback.py` component, including the logic flow, data structures, and sample outputs.

## Overview
The `capture_feedback` Lambda function is the entry point for recording user feedback. It stores the feedback in DynamoDB and triggers a telemetry process for auditing and analytics.

---

## Detailed Code Explanation

### 1. Module Initialization
The module initializes AWS clients and retrieves configuration from environment variables.

```python
import json
import logging
import os
import boto3
import decimal
from datetime import datetime, timezone, timedelta

# ... imports ...

# Initialize AWS clients
dynamodb = boto3.resource("dynamodb")
repo_table = dynamodb.Table(DYNAMO_TABLE) if DYNAMO_TABLE else None
```

### 2. Helper: `DecimalEncoder`
DynamoDB returns numeric types as `Decimal`. This class ensures they are correctly converted to floats during JSON serialization.

### 3. Function: `build_response`
Returns a standardized response for API Gateway, including CORS headers.

**Sample Output**:
```json
{
  "statusCode": 200,
  "headers": {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*"
  },
  "body": "{\"message\": \"Feedback processed successfully\"}"
}
```

### 4. Function: `fetch_user_details`
Queries the `RepoRequest` table using the `ReverseEnggID` to get user context (name, email) for telemetry.

**Sample DB Item**:
```json
{
  "ReverseEnggID": "REQ-123",
  "UserLanId": "jdoe1",
  "FirstName": "John",
  "LastName": "Doe"
}
```

### 5. Function: `prepare_telemetry_properties`
Mappings the raw feedback and user details into a schema that the telemetry service understands.

**Sample Properties**:
```json
{
  "user_info": { "userLanid": "jdoe1", "first_name": "John", ... },
  "thumbs_value": 1,
  "status": "success",
  "lambda": "capture-feedback-lambda"
}
```

---

## Complete Documented Code

```python
# [See capture_feedback.py for the full source code with embedded comments]
```
*(The file `capture_feedback.py` has been updated with detailed inline documentation.)*

---

## Execution Sequence

1.  **Extract**: Get `ReverseEnggID` and feedback from the request body.
2.  **Enrich**: Fetch user metadata from DynamoDB.
3.  **Persist**: Update the DynamoDB record with the feedback.
4.  **Audit**: Prepare and send a payload to the Telemetry Lambda.
5.  **Respond**: Return a 200 OK to the client.
