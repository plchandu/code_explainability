# System Sequence Diagram

This diagram illustrates the operational flows of the Reverse Engineering Agent system, derived from the logic in `code_explain_diagram.py` and the application setup.

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant WebApp as Web App (S3/CloudFront)
    participant APIGW as API Gateway
    participant Lambda as AWS Lambda Functions
    participant SQS as SQS Queues
    participant DDB as DynamoDB
    participant S3 as S3 Bucket
    participant LLM as LLM (Claude 3 / Bedrock)

    rect rgb(240, 240, 240)
    Note over User, LLM: 1. Repository Ingestion & Upload
    User->>WebApp: Upload Repository Archive
    WebApp->>APIGW: Request Pre-signed URL
    APIGW->>Lambda: Trigger Signed S3 URL Lambda
    Lambda-->>WebApp: Return S3 Signed URL
    WebApp->>S3: Store Archive/File
    end

    rect rgb(230, 245, 230)
    Note over User, LLM: 2. Background Processing & KB Sync
    WebApp->>APIGW: Prepare Repo Processing Request
    APIGW->>Lambda: Repo Process Init Lambda
    Lambda->>DDB: Store Processing Request
    Lambda->>SQS: Submit Repo Processing Queue
    SQS->>Lambda: Chunk Process Lambda (Reverse Engineering)
    Lambda->>S3: Get Repository Archive
    Lambda->>LLM: Improve Inline Comments
    Lambda->>SQS: KB Sync Request Queue
    SQS->>Lambda: KB Lambda
    Lambda->>LLM: Initiate KB Sync
    Lambda->>DDB: Update Status (Ready for Query)
    end

    rect rgb(245, 245, 230)
    Note over User, LLM: 3. Documentation Generation
    WebApp->>APIGW: Generate System Documentation
    APIGW->>Lambda: Default Doc Generator Lambda
    Lambda->>LLM: Send Prompt for Docs
    Lambda->>S3: Store Documentation
    Lambda->>DDB: Update Status
    end

    rect rgb(230, 230, 255)
    Note over User, LLM: 4. User Interaction (RAG Flow)
    User->>WebApp: Submit Prompt / Question
    WebApp->>APIGW: Pass Request
    APIGW->>Lambda: Reverse Engineering Prompt Lambda
    Lambda->>DDB: Fetch Relevant Context/Docs
    Lambda->>LLM: Generate Answer based on Context
    LLM-->>User: Return Final Response
    end
```

### Key Components:
- **Auth Layer (not in diagram):** Handled via Amazon Cognito before reaching the API Gateway.
- **Notification:** SES is used to notify users upon completion of processing steps.
- **Queueing:** SQS ensures asynchronous processing of large repository files without blocking the UI.
