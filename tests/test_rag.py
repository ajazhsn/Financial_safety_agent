from sentence_transformers import SentenceTransformer
import chromadb

model = SentenceTransformer("all-MiniLM-L6-v2")
client = chromadb.PersistentClient(path="./fraud_kb_store")
collection = client.get_or_create_collection(name="rbi_trai_fraud_kb")


def search_knowledge_base(query, n_results=3):
    query_embedding = model.encode([query]).tolist()
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=n_results
    )
    return results


# Test with our fake SMS content
query = "KYC will expire, click link to update, account will be blocked"
results = search_knowledge_base(query)

print(f"Query: {query}\n")
print("Top matching knowledge base entries:\n")
for i, (doc, meta) in enumerate(zip(results["documents"][0], results["metadatas"][0])):
    print(f"{i+1}. [{meta['category']}]")
    print(f"   {doc[:150]}...\n")
