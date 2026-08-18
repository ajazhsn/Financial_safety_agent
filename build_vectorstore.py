from sentence_transformers import SentenceTransformer
import chromadb
from rbi_trai_knowledge_base import KNOWLEDGE_BASE

print("Loading embedding model...")
model = SentenceTransformer("all-MiniLM-L6-v2")

print("Setting up vector database...")
client = chromadb.PersistentClient(path="./fraud_kb_store")
collection = client.get_or_create_collection(name="rbi_trai_fraud_kb")

print(f"Embedding {len(KNOWLEDGE_BASE)} knowledge chunks...")
texts = [entry["text"] for entry in KNOWLEDGE_BASE]
ids = [entry["id"] for entry in KNOWLEDGE_BASE]
categories = [entry["category"] for entry in KNOWLEDGE_BASE]

embeddings = model.encode(texts).tolist()

collection.upsert(
    ids=ids,
    embeddings=embeddings,
    documents=texts,
    metadatas=[{"category": c} for c in categories]
)

print(
    f"✅ Vector store built with {collection.count()} entries at ./fraud_kb_store")
