from qdrant_client import AsyncQdrantClient
from qdrant_client import models as qmodels
from sentence_transformers import SentenceTransformer
from config import settings
from typing import List, Optional
import hashlib
import re

# Single embedding model instance (loaded once at startup)
_embedding_model = SentenceTransformer(settings.embedding_model)

# Single shared async Qdrant client
_qdrant_client = AsyncQdrantClient(
    url=settings.qdrant_url,
    api_key=settings.qdrant_api_key,
)

COLLECTION_NAME = "contextkeeper_code"

def embed_text(text: str) -> List[float]:
    """Synchronously embed text. Returns 384-dim vector."""
    vector = _embedding_model.encode(text, normalize_embeddings=True)
    return vector.tolist()

def embed_texts(texts: List[str]) -> List[List[float]]:
    """Batch embed multiple texts."""
    vectors = _embedding_model.encode(texts, normalize_embeddings=True, batch_size=32)
    return [v.tolist() for v in vectors]

def _make_point_id(text: str) -> int:
    """Generate a stable integer ID from a string using MD5."""
    return int(hashlib.md5(text.encode()).hexdigest()[:15], 16)

async def ensure_collection():
    """Create Qdrant collection and ensure payload index exists."""

    exists = await _qdrant_client.collection_exists(COLLECTION_NAME)

    if not exists:
        await _qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=qmodels.VectorParams(
                size=settings.embedding_dim,
                distance=qmodels.Distance.COSINE,
            ),
        )

    # ALWAYS ensure payload index exists
    try:
        await _qdrant_client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name="project_path",
            field_schema=qmodels.PayloadSchemaType.KEYWORD,
        )
    except Exception:
        pass

async def index_chunks(chunks: List[dict], project_path: str):
    """
    Index a list of code chunks into Qdrant.
    Each chunk: {text, file_path, start_line, end_line, function_name, language}
    """
    if not chunks:
        return
    
    await ensure_collection()
    
    texts = [c["text"] for c in chunks]
    vectors = embed_texts(texts)
    
    points = []
    for chunk, vector in zip(chunks, vectors):
        point_id = _make_point_id(f"{project_path}:{chunk['file_path']}:{chunk['start_line']}")
        payload = {
            "project_path": project_path,
            "file_path": chunk["file_path"],
            "start_line": chunk.get("start_line", 0),
            "end_line": chunk.get("end_line", 0),
            "function_name": chunk.get("function_name", ""),
            "language": chunk.get("language", ""),
            "text": chunk["text"][:2000],  # Store first 2000 chars in payload
        }
        points.append(qmodels.PointStruct(id=point_id, vector=vector, payload=payload))
    
    # Upsert in batches of 100 to avoid payload size limits
    batch_size = 100
    for i in range(0, len(points), batch_size):
        batch = points[i:i + batch_size]
        await _qdrant_client.upsert(
            collection_name=COLLECTION_NAME,
            points=batch,
            wait=True,
        )

async def search(query: str, project_path: str, limit: int = 10) -> List[dict]:
    """Search for code chunks relevant to query, filtered by project."""
    await ensure_collection()

    query_vector = embed_text(query)

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

    hits = []
    for scored_point in results:
        payload = scored_point.payload or {}

        hits.append({
            "file_path": payload.get("file_path", ""),
            "start_line": payload.get("start_line", 0),
            "end_line": payload.get("end_line", 0),
            "function_name": payload.get("function_name", ""),
            "language": payload.get("language", ""),
            "text": payload.get("text", ""),
            "score": scored_point.score,
        })

    return hits

async def delete_project_vectors(project_path: str):
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
    """Count how many vectors exist for a project."""
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
