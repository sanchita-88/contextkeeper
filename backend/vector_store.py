import asyncio
import hashlib
from typing import List

from sentence_transformers import SentenceTransformer
from qdrant_client import AsyncQdrantClient
from qdrant_client import models as qmodels

from config import settings

# ---------------------------------------------------------------------------
# Embedding model (loaded once at module startup)
# ---------------------------------------------------------------------------

_model = SentenceTransformer("BAAI/bge-small-en-v1.5")

INSTRUCTION = "Represent this code snippet for semantic search: "

# ---------------------------------------------------------------------------
# Qdrant client (initialized once at module load)
# ---------------------------------------------------------------------------

_qdrant_client = AsyncQdrantClient(
    url=settings.qdrant_url,
    api_key=settings.qdrant_api_key,
)

COLLECTION_NAME = "contextkeeper_code"


# ---------------------------------------------------------------------------
# Embedding helpers
# ---------------------------------------------------------------------------

def _embed_texts_sync(texts: List[str]) -> List[List[float]]:
    """
    Synchronous batch embedding using BAAI/bge-small-en-v1.5.
    Each text is truncated to 2000 chars and prefixed with an instruction.
    Returns a list of 384-dim vectors.
    """
    prepared = [INSTRUCTION + t[:2000] for t in texts]
    vectors = _model.encode(prepared, batch_size=32, show_progress_bar=False)
    return vectors.tolist()


def _embed_text_sync(text: str) -> List[float]:
    """Synchronous single-text embedding."""
    return _embed_texts_sync([text])[0]


async def embed_text(text: str) -> List[float]:
    """Embed a single text asynchronously."""
    return await asyncio.to_thread(_embed_text_sync, text)


async def embed_texts(texts: List[str]) -> List[List[float]]:
    """Embed a list of texts asynchronously."""
    return await asyncio.to_thread(_embed_texts_sync, texts)


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
                size=settings.embedding_dim,  # must be 384 for bge-small-en-v1.5
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