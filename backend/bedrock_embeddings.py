import boto3
import json
import random
import time
from typing import List
from botocore.exceptions import ClientError

client = boto3.client(
    "bedrock-runtime",
    region_name="us-east-1"
)

MODEL_ID = "amazon.titan-embed-text-v2:0"

MAX_RETRIES = 6
INITIAL_RETRY_DELAY = 2.0  # doubles each attempt: 2→4→8→16→32→64s


def embed_text(text: str) -> List[float]:
    """
    Embed a single text using Amazon Titan Embeddings V2.
    Includes exponential backoff with jitter for ThrottlingException.
    Returns a 1024-dim vector.
    """
    body = json.dumps({"inputText": text[:2000]})
    delay = INITIAL_RETRY_DELAY

    for attempt in range(MAX_RETRIES):
        try:
            response = client.invoke_model(
                modelId=MODEL_ID,
                body=body,
                contentType="application/json",
                accept="application/json",
            )
            result = json.loads(response["body"].read())
            return result["embedding"]

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "ThrottlingException":
                if attempt < MAX_RETRIES - 1:
                    jitter = random.uniform(0, delay * 0.3)
                    wait = delay + jitter
                    print(f"Bedrock throttled. Retrying in {wait:.1f}s... (attempt {attempt + 1}/{MAX_RETRIES})")
                    time.sleep(wait)
                    delay *= 2
                else:
                    raise Exception(f"Bedrock embedding failed after {MAX_RETRIES} retries") from e
            else:
                raise

    raise Exception("Bedrock embedding failed: exceeded retry loop")


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Embed a list of texts using Titan. One API call per text.
    Titan does not support multi-text batching.
    """
    return [embed_text(t) for t in texts]