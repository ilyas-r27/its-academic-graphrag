"""Embedding backends: local sentence-transformers or an OpenAI-compatible endpoint."""
from kg import config

_local_model = None


def _prefix(kind: str) -> str:
    # e5 models expect "query: " / "passage: " prefixes
    if "e5" in config.EMBED_MODEL.lower():
        return "query: " if kind == "query" else "passage: "
    return ""


def embed_texts(texts: list[str], kind: str = "passage") -> list[list[float]]:
    """kind: 'passage' for documents, 'query' for questions."""
    texts = [_prefix(kind) + t for t in texts]
    if config.EMBED_BACKEND == "local":
        global _local_model
        if _local_model is None:
            from sentence_transformers import SentenceTransformer

            _local_model = SentenceTransformer(config.EMBED_MODEL)
        return _local_model.encode(texts, normalize_embeddings=True).tolist()

    from openai import OpenAI

    client = OpenAI(base_url=config.EMBED_BASE_URL, api_key=config.EMBED_API_KEY or "none")
    resp = client.embeddings.create(model=config.EMBED_MODEL, input=texts)
    return [d.embedding for d in resp.data]
