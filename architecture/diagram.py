from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import Lambda
from diagrams.aws.database import DynamoDB
from diagrams.aws.storage import S3
from diagrams.aws.network import APIGateway
from diagrams.aws.security import Cognito
from diagrams.aws.analytics import OpenSearchService
from diagrams.aws.ml import sagemaker
from diagrams.aws.network import CloudFront
from diagrams.aws.integration import sqs
from diagrams.aws.engagement import SES

graph_attr = {

    "fontsize": "10",
    "labelloc": "t"
    
    
}

with Diagram("Reverse Engineering Agent AWS Architecture", show=True, graph_attr=graph_attr, direction="LR") as diag:
    # Clusters
    user = CloudFront("User Zone")
    web_app = S3("Web App")
    dynamodb_reporequest= DynamoDB("DynamoDB table")
    s3_bucket= S3("S3 Bucket")


    repo_process_init_lambda=Lambda("Repository Processing init Lambda")
    chunk_process_lambda=Lambda("inline comments Processing Lambda")
    reverseeng_prompt_lambda=Lambda("Reverse Engineering Prompt Lambda")
    signeds3url_lambda=Lambda("Signed S3 URL Lambda")
    kb_lambda=Lambda("Knowledge Base Lambda")
    repo_doc_generator_lambda=Lambda("Default Doc Generator Lambda")

    repo_process_queue=sqs("Repository Processing Queue")
    commented_files_kb_sync_queue=sqs("KB Sync request")
    email_notification = SES("Email Notification")
    ce_doc_view_lambda=Lambda("CE Doc View Lambda")

    llm = SageMaker("LLM(claud 3)")

    api_gateway = APIGateway("API Gateway")

    #document upload flow
    user >> edge(label="0 upload archieve")>> web_app
    web_app >> edge(label="1 get pre-signed url",minlen=3 ) >> api_gateway
    api_gateway >> edge(label="2 get pre-signed url",minlen="5") >> signeds3url_lambda
    signeds3url_lambda >> edge(label="3 get pre-signed url",minlen="6") >> s3_bucket
    s3_bucket >> edge(label="4 store archieve file",minlen="8") >> s3_bucket

    
    
    # Data upload to S3 ,now submit to be to process
    web_app >> edge(label="5 prepare repo processing request",minlen="8") >> api_gateway
    api_gateway >> edge(label="6 trigger lambda for repo processing",minlen="8") >> repo_process_init_lambda
    repo_process_init_lambda >> edge(label="7 store repo processing request",minlen="8") >> dynamodb_reporequest
    repo_process_init_lambda >> edge(label="8 submit repo for processing",minlen="8") >> repo_process_queue
    repo_process_init_lambda >> edge(label="9 trigger email notification",minlen="8") >> email_notification


    repo_process_queue >> edge(label="8.1 trigger the chunking mechanism for reverse engneeringid",minlen="8") >> chunk_process_lambda
    chunk_process_lambda >> edge(label="8.2 get the object to process ",minlen="2") >> dynamodb_reporequest
    chunk_process_lambda >> edge(label="8.3 get the repo archive file from S3",minlen="2") >> s3_bucket
    chunk_process_lambda >> edge(label="8.4 improve inline comments",minlen="2") >> llm
    chunk_process_lambda >> edge(label="8.5 message for kb sync",minlen="2") >> commented_files_kb_sync_queue
    commented_files_kb_sync_queue >> edge(label="8.5.1 trigger the kb sync lambda",minlen="2") >> kb_lambda
    kb_lambda >> edge(label="8.5.2 initiate kb sync with s3 objects ",minlen="2") >> llm
    kb_lambda >> edge(label="8.5.3 update status ready for query ",minlen="2") >> dynamodb_reporequest
    

    #get default system documentation
    web_app >> edge(label="9 generate reverse engineering system documentation",minlen="8") >> api_gateway
    api_gateway >> edge(label="10 trigger lambda for documentation generation",minlen="8") >> repo_doc_generator_lambda
    repo_doc_generator_lambda >> edge(label="11 send prompt to llm for documentation generation",minlen="8") >> llm
    repo_doc_generator_lambda >> edge(label="12 store the documentation in s3",minlen="8") >> s3_bucket
    repo_doc_generator_lambda >> edge(label="13 update status ready for query ",minlen="8") >> dynamodb_reporequest
    repo_doc_generator_lambda >> edge(label="13 trigger email notification",minlen="8") >> email_notification
    
    # request accessing code explainability documents
    web_app >> edge(label="14 request accessing code explainability documents",minlen="8") >> api_gateway
    api_gateway >> edge(label="15 trigger lambda for code explainability documents",minlen="8") >> ce_doc_view_lambda
    ce_doc_view_lambda >> edge(label="16 list docs and their links",minlen="8") >> dynamodb_reporequest
    

    # process the new prompts
    web_app >> edge(label="17 submit new user prompt for code explainability",minlen="8") >> api_gateway
    api_gateway >> edge(label="18 trigger lambda for code explainability",minlen="8") >> reverseeng_prompt_lambda
    reverseeng_prompt_lambda >> edge(label="19 get the code explainability documents from s3",minlen="8") >> dynamodb_reporequest
    reverseeng_prompt_lambda >> edge(label="20 get the response for prompt message",minlen="8") >> llm
    
    

    
    