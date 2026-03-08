from sentence_transformers import SentenceTransformer

model = SentenceTransformer("BAAI/bge-small-en-v1.5")

def embed_text(text: str):
    return model.encode(text[:2000]).tolist()

def embed_texts(texts):
    truncated = [t[:2000] for t in texts]
    return model.encode(truncated).tolist()