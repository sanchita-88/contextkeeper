import boto3
import json

client = boto3.client(
    "bedrock-runtime",
    region_name="us-west-2"
)

body = json.dumps({
    "inputText": "hello world"
})

response = client.invoke_model(
    modelId="amazon.titan-embed-text-v2:0",
    body=body,
    contentType="application/json",
    accept="application/json"
)

result = json.loads(response["body"].read())

print(len(result["embedding"]))
print(result["embedding"][:10])