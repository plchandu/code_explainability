import sys
import os
import importlib.util

# Get the absolute path of the directory where debug_runner.py is located
current_dir = os.path.dirname(os.path.abspath(__file__))
# The authorizer.py file path (two levels up from this script in the 'authorizer' folder)
authorizer_path = os.path.abspath(os.path.join(current_dir, "../../authorizer.py"))

# Robustly import the authorizer module by its file path
if not os.path.exists(authorizer_path):
    print(f"Error: Could not find authorizer.py at {authorizer_path}")
    sys.exit(1)

spec = importlib.util.spec_from_file_location("authorizer", authorizer_path)
authorizer = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(authorizer)
    lambda_handler = authorizer.lambda_handler
except Exception as e:
    print(f"Error loading authorizer.py: {e}")
    sys.exit(1)

os.environ['ISSUER'] = 'https://cognito-idp.us-east-1.amazonaws.com/your-user-pool-id'

mock_event = {
    "headers": {
        "Authorization": "Bearer YOUR_JWT_HERE"
    },
    "methodArn": "arn:aws:execute-api:..."
}

if __name__ == "__main__":
    print("Running lambda_handler with mock event...")
    result = lambda_handler(mock_event, None)
    print("Result:")
    print(result)