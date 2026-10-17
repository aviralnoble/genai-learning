import chromadb

# =====================================================================
# 1. INITIALIZE CLIENT
# =====================================================================
# Using PersistentClient saves SQLite and index data to a local directory.
client = chromadb.PersistentClient(path="chroma_data")
print("1. Client initialized. Target directory: ./chroma_data")


# =====================================================================
# 2. CREATE A COLLECTION
# =====================================================================
# "hnsw:space" defines how similarity is calculated:
# - "cosine" (0 = identical, 1 = orthogonal/unrelated, 2 = opposite)
# - "l2" (squared Euclidean distance)
# - "ip" (inner product)
collection = client.get_or_create_collection(
    name="tech_kb",
    metadata={"hnsw:space": "cosine"}
)
print(f"2. Collection '{collection.name}' ready.")


# =====================================================================
# 3. ADD DOCUMENTS
# =====================================================================
# Chroma converts 'documents' into numerical vectors automatically
# using an internal sentence-transformers model.
collection.add(
    documents=[
        "Python is an interpreted, high-level programming language known for readability.",
        "PostgreSQL is a powerful, open-source object-relational database system.",
        "FastAPI is a modern, fast web framework for building APIs with Python.",
        "Vector databases index high-dimensional embeddings to perform semantic search.",
        "Docker packages applications and dependencies into standardized containers.",
    ],
    metadatas=[
        {"category": "language", "level": "beginner"},
        {"category": "database", "level": "intermediate"},
        {"category": "framework", "level": "intermediate"},
        {"category": "database", "level": "advanced"},
        {"category": "devops", "level": "intermediate"},
    ],
    ids=["doc_py", "doc_pg", "doc_fa", "doc_vec", "doc_dk"]
)
print(f"3. Added documents. Total records in collection: {collection.count()}")


# =====================================================================
# 4. INSPECT & RETRIEVE (EXACT FETCH)
# =====================================================================
# peek() retrieves the first few items in the collection
print("\n--- PEEK FIRST 2 RECORDS ---")
print(collection.peek(limit=2)["documents"])

# get() fetches by exact ID or condition without doing a semantic vector search
print("\n--- GET BY ID ---")
fetched_item = collection.get(
    ids=["doc_py"],
    include=["documents", "metadatas"]
)
print("Fetched doc:", fetched_item["documents"][0])
print("Metadata:", fetched_item["metadatas"][0])


# =====================================================================
# 5. SEMANTIC SEARCH (QUERY)
# =====================================================================
# Searching concepts rather than matching exact keywords
query_text = "What tool should I use to build REST endpoints quickly?"

results = collection.query(
    query_texts=[query_text],
    n_results=2,
    include=["documents", "metadatas", "distances"]
)

print(f"\n--- SEMANTIC SEARCH FOR: '{query_text}' ---")
for i in range(len(results["ids"][0])):
    doc_id = results["ids"][0][i]
    doc = results["documents"][0][i]
    meta = results["metadatas"][0][i]
    dist = results["distances"][0][i]
    print(f"Rank {i+1} [ID: {doc_id} | Distance: {dist:.4f}]")
    print(f"  Content: {doc}")
    print(f"  Category: {meta['category']}\n")


# =====================================================================
# 6. FILTERED QUERY (METADATA & DOCUMENT FILTERING)
# =====================================================================
# You can filter by metadata fields using the 'where' parameter
# Operators available: $eq, $ne, $gt, $gte, $lt, $lte, $in, $nin, $and, $or
filtered_results = collection.query(
    query_texts=["data storage systems"],
    n_results=2,
    where={"category": {"$eq": "database"}},  # Only search items where category == 'database'
)
print("--- FILTERED SEARCH (category == 'database') ---")
print("Matches:", filtered_results["ids"][0])


# =====================================================================
# 7. UPDATE VS. UPSERT
# =====================================================================
# update() modifies existing records; fails if the ID doesn't exist
collection.update(
    ids=["doc_py"],
    documents=["Python 3.12+ features improved performance and better error tracebacks."],
    metadatas=[{"category": "language", "level": "all-levels"}]
)

# upsert() updates if the ID exists, or inserts if it does not
collection.upsert(
    ids=["doc_py", "doc_k8s"],
    documents=[
        "Python is a versatile language used heavily in AI and Data Science.",
        "Kubernetes automates deployment and scaling of containerized apps."
    ],
    metadatas=[
        {"category": "language", "level": "all-levels"},
        {"category": "devops", "level": "advanced"}
    ]
)
print(f"7. After upsert, total records: {collection.count()}")


# =====================================================================
# 8. DELETE RECORDS & CLEANUP
# =====================================================================
# Delete specific records by ID
collection.delete(ids=["doc_k8s"])
print(f"8. Deleted 'doc_k8s'. Remaining records: {collection.count()}")

# Delete records matching a metadata condition
collection.delete(where={"level": "beginner"})

# List all collections in the database
all_colls = client.list_collections()
print(f"Active collections in client: {[c.name for c in all_colls]}")

# To permanently drop an entire collection:
# client.delete_collection(name="tech_kb")