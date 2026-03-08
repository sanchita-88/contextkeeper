import boto3
import json
import time
from typing import List
from botocore.exceptions import ClientError

client = boto3.client(
    "bedrock-runtime",
    region_name="us-east-1"
)

MODEL_ID = "cohere.embed-english-v3"


def embed_text(text: str) -> List[float]:
    """
    Generate embedding using Cohere Embed English v3.
    Includes retry logic with exponential backoff to handle throttling.
    """

    body = json.dumps({
    "texts": [text[:2000]],
    "input_type": "search_document",
    "truncate": "END"
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
            return result["embeddings"][0]

        except ClientError as e:
            if "Throttling" in str(e):
                print(f"Bedrock throttled. Retrying in {delay}s... (attempt {attempt + 1}/{retries})")
                time.sleep(delay)
                delay *= 2
            else:
                raise

    raise Exception("Bedrock embedding failed after retries exhausted")