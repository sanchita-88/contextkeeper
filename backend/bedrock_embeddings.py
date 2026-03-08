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

# Cohere V4 supports true multi-text batching — one API call for up to 96 texts
MODEL_ID = "cohere.embed-v4:0"

MAX_RETRIES = 6
INITIAL_RETRY_DELAY = 2.0  # doubles each attempt: 2→4→8→16→32→64s


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Batch embedding using Cohere Embed V4 on AWS Bedrock.
    Accepts up to 96 texts per call. Returns one vector per input text.
    Includes exponential backoff with jitter for ThrottlingException.
    """
    # Truncate each text to stay within token limits
    texts = [t[:2000] for t in texts]

    body = json.dumps({
        "texts": texts,
        "input_type": "search_document",
    })

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
            return result["embeddings"]  # list of vectors, one per input text

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


def embed_text(text: str) -> List[float]:
    """
    Convenience wrapper to embed a single text.
    """
    return embed_texts([text])[0]