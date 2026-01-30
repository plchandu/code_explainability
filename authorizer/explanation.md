# Authorizer Code Explanation

This document explains the functionality of the **AWS Lambda Custom Authorizer** with sample values and detailed breakdowns.

## Overview
The authorizer intercepts requests coming into an API Gateway, validates a JWT (Json Web Token), and returns an IAM Policy that either **Allows** or **Denies** the request.

---

## 1. Sample Input (The Lambda Event)
When a user calls your API with a header like `Authorization: Bearer <TOKEN>`, AWS Lambda receives an `event` like this:

```json
{
    "type": "TOKEN",
    "methodArn": "arn:aws:execute-api:us-east-1:123456789012:apiId/dev/GET/my-resource",
    "headers": {
        "Authorization": "Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IjEyMzQ1In0..."
    }
}
```

---

## 2. Code Breakdown

### `lambda_handler(event, context)`
This is the entry point. It extracts the token and calls the validation logic.

```python
def lambda_handler(event, context):
    # 1. Extract the 'Bearer <token>' string
    auth_header = event.get("headers", {}).get("Authorization", "")
    
    # Sample Value: "Bearer eyJhbG..." -> token = "eyJhbG..."
    token = auth_header.split(" ")[1]
    method_arn = event.get("methodArn")
        
    try:
        # 2. Validate the token
        validate_token(token)
        # 3. If valid, return a "Allow" policy
        return generate_policy("user", "Allow", method_arn, 200, 'authorized token')
    except Exception as e:
        # 4. If invalid, return a "Deny" policy
        return generate_policy("user", "Deny", method_arn, 401, 'unauthorized', str(e))
```

### `validate_token(token)`
Checks if the token is authentic. It uses the `kid` (Key ID) from the token header to identify the correct public key for verification.

```python
def validate_token(token):
    # 1. Get the 'kid' from the JWT header without verifying yet
    # Sample Header: {"alg": "RS256", "kid": "12345"}
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")

    # 2. Fetch the specific RSA public key from the JWKS provider (e.g., Cognito)
    rsa_key = get_public_keys(kid)

    # 3. Verify the signature and decode the payload
    # Sample Payload: {"sub": "user_123", "exp": 1700000000, "name": "John Doe"}
    payload = jwt.decode(token, rsa_key, algorithms=["RS256"], ...)
    return payload
```

### `get_public_keys(kid)`
Connects to the `ISSUER` URL (e.g., Cognito) to fetch the list of trusted public keys.

*   **Sample JWKS Response**:
    ```json
    {
      "keys": [
        { "kid": "12345", "alg": "RS256", "n": "...", "e": "AQAB", "kty": "RSA" }
      ]
    }
    ```

### `generate_policy(...)`
Constructs the final JSON response required by AWS API Gateway.

*   **Sample "Allow" Result**:
    ```json
    {
        "principalId": "user",
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "execute-api:Invoke",
                    "Effect": "Allow",
                    "Resource": "arn:aws:execute-api:us-east-1:123456789012:..."
                }
            ]
        },
        "context": {
            "custom_code": 200,
            "custom_message": "authorized token",
            "error_message": ""
        }
    }
    ```

---

## 3. Execution Flow Summary
1.  **Client** sends a request with an `Authorization` header.
2.  **API Gateway** triggers the Lambda Authorizer.
3.  **Lambda** downloads **Public Keys** from the Identity Provider (Cognito).
4.  **Lambda** verifies the **JWT Signature** using those keys.
5.  **Lambda** returns a policy to API Gateway (**Allow** or **Deny**).
6.  **API Gateway** processes the policy:
    *   **Allow**: Forwards the request to the backend.
    *   **Deny**: Returns a **401 Unauthorized** error.
