import asyncio
import hashlib
import json
import random
import time
from typing import List

import boto3
from botocore.exceptions import ClientError
from qdrant_client import AsyncQdrantClient
from qdrant_client import models as qmodels

from config import settings

# ---------------------------------------------------------------------------
# Bedrock client (initialized once at module load)
# ---------------------------------------------------------------------------

_bedrock_client = boto3.client(
    "bedrock-runtime",
    region_name="us-east-1",
)

MODEL_ID = "amazon.titan-embed-text-v2:0"

# 600 RPM = 10 RPS available — no sleep needed, backoff handles rare throttles
MAX_RETRIES = 6
INITIAL_RETRY_DELAY = 2.0   # doubles each attempt: 2→4→8→16→32→64s
EMBED_BATCH_SIZE = 20        # logical batch size for embed_texts

# ---------------------------------------------------------------------------
# Qdrant client (initialized once at module load)
# ---------------------------------------------------------------------------

_qdrant_client = AsyncQdrantClient(
    url=settings.qdrant_url,
    api_key=settings.qdrant_api_key,
)

COLLECTION_NAME = "contextkeeper_code"


# ---------------------------------------------------------------------------
# Low-level Bedrock helpers (synchronous — called via asyncio.to_thread)
# ---------------------------------------------------------------------------

def _invoke_titan_sync(text: str) -> List[float]:
    """
    Embed a single text via Bedrock Titan with exponential backoff + jitter.
    Titan does not support multi-text batching — one call per text.
    """
    body = json.dumps({"inputText": text[:2000]})
    delay = INITIAL_RETRY_DELAY

    for attempt in range(MAX_RETRIES):
        try:
            response = _bedrock_client.invoke_model(
                modelId=MODEL_ID,
                body=body,
                contentType="application/json",
                accept="application/json",
            )
            result = json.loads(response["body"].read())
            return result["embedding"]

        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ThrottlingException":
                if attempt < MAX_RETRIES - 1:
                    jitter = random.uniform(0, delay * 0.3)
                    wait = delay + jitter
                    print(
                        f"[bedrock] ThrottlingException — retrying in {wait:.1f}s "
                        f"(attempt {attempt + 1}/{MAX_RETRIES})"
                    )
                    time.sleep(wait)
                    delay *= 2
                else:
                    raise RuntimeError(
                        f"Bedrock embedding failed after {MAX_RETRIES} retries"
                    ) from exc
            else:
                raise

    raise RuntimeError("Bedrock embedding failed: exceeded retry loop")


def _embed_batch_sync(texts: List[str]) -> List[List[float]]:
    """Embed a list of texts synchronously, one Bedrock call per text."""
    return [_invoke_titan_sync(t) for t in texts]


# ---------------------------------------------------------------------------
# Public async embedding helpers
# ---------------------------------------------------------------------------

async def embed_text(text: str) -> List[float]:
    """Embed a single text asynchronously."""
    return await asyncio.to_thread(_invoke_titan_sync, text)


async def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Embed a list of texts in batches, each run in a thread pool.
    Titan outputs 1024-dim vectors. Texts truncated to 2000 chars.
    """
    truncated = [t[:2000] for t in texts]
    all_vectors: List[List[float]] = []

    for i in range(0, len(truncated), EMBED_BATCH_SIZE):
        batch = truncated[i : i + EMBED_BATCH_SIZE]
        batch_vectors = await asyncio.to_thread(_embed_batch_sync, batch)
        all_vectors.extend(batch_vectors)

    return all_vectors


# ---------------------------------------------------------------------------
# Qdrant helpers
# ---------------------------------------------------------------------------

def _make_point_id(text: str) -> int:
    """Generate a stable integer ID from a string using MD5."""
    return int(hashlib.md5(text.encode()).hexdigest()[:15], 16)


async def ensure_collection() -> None:
    """Create the Qdrant collection and ensure the payload index exists."""
    exists = await _qdrant_client.collection_exists(COLLECTION_NAME)

    if not exists:
        await _qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=qmodels.VectorParams(
                size=settings.embedding_dim,  # must be 1024 for Titan v2
                distance=qmodels.Distance.COSINE,
            ),
        )

    # Idempotent: silently ignore "already exists" errors
    try:
        await _qdrant_client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name="project_path",
            field_schema=qmodels.PayloadSchemaType.KEYWORD,
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Public API (signatures unchanged)
# ---------------------------------------------------------------------------

async def index_chunks(chunks: List[dict], project_path: str) -> None:
    """
    Embed and index a list of code chunks into Qdrant.

    Each chunk dict must contain:
        text, file_path, start_line, end_line, function_name, language
    """
    if not chunks:
        return

    await ensure_collection()

    texts = [c["text"] for c in chunks]
    vectors = await embed_texts(texts)

    points: List[qmodels.PointStruct] = []
    for chunk, vector in zip(chunks, vectors):
        point_id = _make_point_id(
            f"{project_path}:{chunk['file_path']}:{chunk['start_line']}"
        )
        payload = {
            "project_path": project_path,
            "file_path": chunk["file_path"],
            "start_line": chunk.get("start_line", 0),
            "end_line": chunk.get("end_line", 0),
            "function_name": chunk.get("function_name", ""),
            "language": chunk.get("language", ""),
            "text": chunk["text"][:2000],
        }
        points.append(
            qmodels.PointStruct(id=point_id, vector=vector, payload=payload)
        )

    # Upsert in batches of 100 to stay within Qdrant payload size limits
    for i in range(0, len(points), 100):
        await _qdrant_client.upsert(
            collection_name=COLLECTION_NAME,
            points=points[i : i + 100],
            wait=True,
        )


async def search(
    query: str, project_path: str, limit: int = 10
) -> List[dict]:
    """Search for code chunks relevant to query, filtered by project."""
    await ensure_collection()

    query_vector = await embed_text(query)

    project_filter = qmodels.Filter(
        must=[
            qmodels.FieldCondition(
                key="project_path",
                match=qmodels.MatchValue(value=project_path),
            )
        ]
    )

    results = await _qdrant_client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        query_filter=project_filter,
        limit=limit,
        with_payload=True,
    )

    return [
        {
            "file_path": (p := scored.payload or {}).get("file_path", ""),
            "start_line": p.get("start_line", 0),
            "end_line": p.get("end_line", 0),
            "function_name": p.get("function_name", ""),
            "language": p.get("language", ""),
            "text": p.get("text", ""),
            "score": scored.score,
        }
        for scored in results
    ]


async def delete_project_vectors(project_path: str) -> None:
    """Delete all vectors for a project from Qdrant."""
    await ensure_collection()
    await _qdrant_client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=qmodels.FilterSelector(
            filter=qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="project_path",
                        match=qmodels.MatchValue(value=project_path),
                    )
                ]
            )
        ),
        wait=True,
    )


async def count_project_vectors(project_path: str) -> int:
    """Return the number of vectors stored for a given project."""
    await ensure_collection()
    result = await _qdrant_client.count(
        collection_name=COLLECTION_NAME,
        count_filter=qmodels.Filter(
            must=[
                qmodels.FieldCondition(
                    key="project_path",
                    match=qmodels.MatchValue(value=project_path),
                )
            ]
        ),
        exact=True,
    )
    return result.count