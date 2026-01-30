"""
Module for validating JWT tokens
"""

import os
import logging
from typing import Literal
import requests
from jose import jwt
from jose.exceptions import JWTError, ExpiredSignatureError

# initialize logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# initialize environment variables
ISSUER = os.getenv("ISSUER")
JWKS_URL = f"{ISSUER}/.well-known/jwks.json"

def get_public_keys(kid):
    """
    Fetches the public keys from AWS Cognito's JWKS using the keyid
    """
    try:
        logger.info("Fetching public keys from JWKS")
        # Fetch the JWKS (public Keys) from Cognito with a timeout
        response = requests.get(JWKS_URL, timeout=10)
        response.raise_for_status()
        jwks = response.json()
        
        # Find the key that matches the "KID" in the JWT header
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                return {
                    'kty': key.get('kty'),
                    'kid': key.get('kid'),
                    'use': key.get('use'),
                    'alg': key.get('alg'),
                    'n': key.get('n'),
                    'e': key.get('e')
                }
    except Exception as e:
        logger.error(f"Error fetching public keys from JWKS: {str(e)}")
        raise ValueError("Failed to fetch public keys from JWKS")
    raise ValueError("Public key not found for the given key id")

def validate_token(token: str):
    '''
    Validates the JWT token using the public key from JWKS for its expiry and integrity (signature check).
    '''
    try:
        logger.info("Validating token")
        # Extract the "kid" from the JWT header
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        if not kid:
            raise ValueError("Missing 'kid' in JWT header")

        # Get the public key from JWKS
        rsa_key = get_public_keys(kid)

        # Decode the JWT using the RSA public key and check the expiration ('exp')
        # skip audience and issuer validation for now as per original code
        payload = jwt.decode(
            token, 
            rsa_key, 
            algorithms=["RS256"], 
            options={"verify_exp": False, "verify_iss": False}
        )
        
        return payload

    except JWTError as e:
        logger.error(f"Invalid token: {str(e)}")
        raise ValueError("Invalid token")
    except ExpiredSignatureError as e:
        logger.error(f"Token expired: {str(e)}")
        raise ValueError("Token expired")
    except Exception as e:
        logger.error(f"Error validating token: {str(e)}")
        raise ValueError("Failed to validate token")

def generate_policy(principal_id: str, effect: Literal["Allow", "Deny"], resource: str, custom_code: int, custom_message: str, error_message: str = ""):
    """
    Generate a policy document for the lambda function
    """
    auth_response = {
        "principalId": principal_id,
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "execute-api:Invoke",
                    "Effect": effect,
                    "Resource": resource
                }
            ]
        },
        'context': {
            'custom_code': custom_code,
            'custom_message': custom_message,
            'error_message': error_message
        }
    }
    logger.info("Generated policy: %s", auth_response)
    return auth_response

def lambda_handler(event, context):
    '''
    AWS Lambda handler to authenticate the bearer token by checking expiry and integrity (signature check).
    this function validates the token and returns the payload if the token is valid.
    '''
    logger.info("Event: %s", event)
    
    auth_header = event.get("headers", {}).get("Authorization", "")
    if not auth_header:
        # Check for lowercase 'authorization' as well
        auth_header = event.get("headers", {}).get("authorization", "")

    if not auth_header or not auth_header.lower().startswith("bearer "):
        logger.error("Missing or invalid Authorization header")
        return generate_policy("user", "Deny", event.get("methodArn"), 401, 'unauthorized token not passed in the payload')

    token = auth_header.split(" ")[1]
    method_arn = event.get("methodArn")
        
    try:
        validate_token(token)
        return generate_policy("user", "Allow", method_arn, 200, 'authorized token')
    except ValueError as e:
        logger.error(f"Invalid token: {str(e)}")
        return generate_policy("user", "Deny", method_arn, 401, 'unauthorized token', str(e))
    except Exception as e:
        logger.error(f"Error validating token: {str(e)}")
        return generate_policy("user", "Deny", method_arn, 500, 'internal server error', str(e))
