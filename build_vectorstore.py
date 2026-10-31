"""
Builds the RBI/TRAI/NPCI knowledge base with a MULTILINGUAL embedding model.

v1 used all-MiniLM-L6-v2, which is English-only: a Hindi/Tamil message was
embedded into a space it was never trained on, so retrieval was close to random.
paraphrase-multilingual-MiniLM-L12-v2 maps Hindi, Tamil, English etc. into the
same space, so a Hindi KYC scam lands next to the English KYC advisory.
"""

import chromadb
from sentence_transformers import SentenceTransformer

from rbi_trai_knowledge_base import KNOWLEDGE_BASE

EMBED_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
COLLECTION = "rbi_trai_fraud_kb_multi"

if __name__ == "__main__":
    print(f"Loading {EMBED_MODEL} ...")
    model = SentenceTransformer(EMBED_MODEL)

    client = chromadb.PersistentClient(path="./fraud_kb_store")
    try:
        client.delete_collection(COLLECTION)  # rebuild from scratch
    except Exception:
        pass
    collection = client.create_collection(COLLECTION)

    texts = [e["text"] for e in KNOWLEDGE_BASE]
    collection.add(
        ids=[e["id"] for e in KNOWLEDGE_BASE],
        embeddings=model.encode(texts).tolist(),
        documents=texts,
        metadatas=[{"category": e["category"]} for e in KNOWLEDGE_BASE],
    )
    print(f"Done: {collection.count()} entries in '{COLLECTION}'")
