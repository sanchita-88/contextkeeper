import boto3
import json
import time
from typing import List
from botocore.exceptions import ClientError

# Bedrock client
client = boto3.client(
    "bedrock-runtime",
    region_name="us-east-1"
)

MODEL_ID = "amazon.titan-embed-text-v2:0"


def embed_text(text: str) -> List[float]:
    """
    Generate embedding using Amazon Titan Embeddings v2.
    Includes retry logic with exponential backoff.
    """

    # Titan limit ~8k tokens but we keep safe
    text = text[:2000]

    body = json.dumps({
        "inputText": text
    })

    retries = 5
    delay = 1

    for attempt in range(retries):
        try:
            response = client.invoke_model(
                modelId=MODEL_ID,
                body=body,
                contentType="application/json",
                accept="application/json"
            )

            result = json.loads(response["body"].read())

            return result["embedding"]

        except ClientError as e:

            if "ThrottlingException" in str(e):
                print(f"Bedrock throttled. Retrying in {delay}s... (attempt {attempt+1}/{retries})")
                time.sleep(delay)
                delay *= 2

            else:
                raise

    raise Exception("Bedrock embedding failed after retries exhausted")