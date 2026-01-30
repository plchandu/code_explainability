# Chunk Cleanup - Documentation

The `chunk_cleanup.py` module is a utility Lambda function designed to maintain S3 storage efficiency by removing temporary file chunks after they have been processed.

## Functionality
- **Input**: Receives a list of S3 object keys (`Chunk_keys`).
- **Process**: Iterates through each key and attempts to delete the object from the configured S3 bucket (`S3_BUCKET_NAME`).
- **Error Handling**: 
    - Continues deleting other chunks even if one fails.
    - Logs errors for any failed deletions.
    - Returns a 500 status code only if a critical exception occurs outside the individual chunk deletion loop.

## Configuration (Environment Variables)
- `REGION_NAME`: The AWS region (e.g., `ap-south-1`).
- `S3_BUCKET_NAME`: The bucket where chunks are stored.

## Data Structures

### Sample Event (Input)
```json
{
  "ReverseEnggID": "REF-ID-001",
  "FilePath": "original/file.zip",
  "Chunk_keys": [
    "chunks/part_1.bin",
    "chunks/part_2.bin"
  ]
}
```

### Response (Output)
```json
{
  "statusCode": 200,
  "body": "{\"message\": \"Chunks deleted successfully\"}"
}
```

## Logic Flow
1. **Initialize**: S3 client is initialized globally.
2. **Handle Event**: `lambda_handler` extracts the list of keys.
3. **Loop & Delete**: 
    - For each `chunk` in `Chunk_keys`:
        - Call `s3_client.delete_object`.
        - Log success or `ClientError`.
4. **Final Response**: Return standardized JSON response.
