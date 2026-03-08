import boto3
import json

client = boto3.client(
    "bedrock-runtime",
    region_name="us-west-2"
)

MODEL_ID = "amazon.titan-embed-text-v2:0"


def embed_text(text: str):
    body = json.dumps({
        "inputText": text
    })

    response = client.invoke_model(
        modelId=MODEL_ID,
        body=body,
        contentType="application/json",
        accept="application/json"
    )

    result = json.loads(response["body"].read())

    return result["embedding"]