"""
Unofficial Guide: Organic Chemistry RAG Pipeline
Stage 3 — Embedding
Stage 4 — Vector Store + Retrieval

Embedding model : multi-qa-MiniLM-L6-cos-v1 (sentence-transformers, runs locally)
                  Trained on Q&A pairs — better at matching student questions
                  to relevant chunks than general-purpose models.
Vector store    : ChromaDB (persistent, on-disk)

Usage:
    # Build the vector store from chunks.jsonl
    python embed_and_retrieve.py --build

    # Query the vector store
    python embed_and_retrieve.py --query "What is the difference between SN1 and SN2?"
"""

import os
import json
import argparse
from typing import Optional

from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CHUNKS_FILE   = "chunks.jsonl"
CHROMA_DIR    = "chroma_db"                    # persistent on-disk vector store
COLLECTION    = "orgo_guide_v2"               # new collection — fresh build with new model
EMBED_MODEL   = "multi-qa-MiniLM-L6-cos-v1"  # Q&A-trained, better for student queries

# Dynamic top-k — adjust via query call or environment variable
DEFAULT_TOP_K = int(os.getenv("TOP_K", 5))


# ---------------------------------------------------------------------------
# Stage 3: Embedding model
# ---------------------------------------------------------------------------

def load_embedding_model(model_name: str = EMBED_MODEL) -> SentenceTransformer:
    """
    Load the sentence-transformers embedding model.
    multi-qa-MiniLM-L6-cos-v1 is trained on question-answer pairs, making it
    significantly better at matching student questions to relevant chunk text
    than general-purpose models like all-MiniLM-L6-v2.
    Runs entirely locally — no API key, no rate limits.
    First run downloads the model (~80MB); subsequent runs load from cache.
    """
    print(f"Loading embedding model: {model_name} ...")
    model = SentenceTransformer(model_name)
    print("  ✅ Model loaded")
    return model


# ---------------------------------------------------------------------------
# Stage 4: ChromaDB vector store
# ---------------------------------------------------------------------------

def get_chroma_collection(
    persist_dir: str = CHROMA_DIR,
    collection_name: str = COLLECTION,
) -> tuple[chromadb.Collection, chromadb.PersistentClient]:
    """
    Connect to (or create) a persistent ChromaDB collection.

    ChromaDB stores vectors and metadata on disk at `persist_dir`.
    The collection acts as the searchable index for all embedded chunks.

    Returns both the collection and client so the caller can manage
    the client lifecycle if needed.
    """
    client = chromadb.PersistentClient(
        path=persist_dir,
        settings=Settings(anonymized_telemetry=False),
    )
    collection = client.get_or_create_collection(
        name=collection_name,
        # cosine distance is standard for sentence-transformer embeddings
        metadata={"hnsw:space": "cosine"},
    )
    return collection, client


# ---------------------------------------------------------------------------
# Build: load chunks → embed → store in ChromaDB
# ---------------------------------------------------------------------------

def load_chunks(path: str = CHUNKS_FILE) -> list[dict]:
    """Load all chunks from the JSONL file produced by ingest_and_chunk.py."""
    chunks = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                chunks.append(json.loads(line))
    return chunks


def build_vector_store(
    chunks_file: str  = CHUNKS_FILE,
    persist_dir: str  = CHROMA_DIR,
    model_name: str   = EMBED_MODEL,
    batch_size: int   = 32,
) -> None:
    """
    Embed all chunks and load them into ChromaDB with source metadata.

    Each chunk is stored with:
      - embedding  : dense vector from all-MiniLM-L6-v2
      - document   : raw chunk text (returned alongside results at query time)
      - metadata   : source, source_url, topic, content_type, chunk_index,
                     total_chunks — used for attribution and filtering

    Batching keeps memory usage low for larger corpora.
    Existing entries with the same chunk_id are skipped (idempotent).
    """
    print("\n" + "=" * 60)
    print("Stage 3 & 4 — Embedding + Vector Store Build")
    print("=" * 60)

    # Load chunks
    print(f"\nLoading chunks from '{chunks_file}' ...")
    chunks = load_chunks(chunks_file)
    print(f"  Loaded {len(chunks)} chunks")

    # Load embedding model
    model = load_embedding_model(model_name)

    # Connect to ChromaDB
    collection, _ = get_chroma_collection(persist_dir)

    # Check for existing entries to avoid re-embedding
    existing_ids = set(collection.get(include=[])["ids"])
    new_chunks   = [c for c in chunks if c["chunk_id"] not in existing_ids]

    if not new_chunks:
        print(f"\n  ✅ All {len(chunks)} chunks already in vector store — nothing to do.")
        return

    print(f"\n  {len(new_chunks)} new chunks to embed "
          f"({len(existing_ids)} already stored)")

    # Embed and store in batches
    total_stored = 0
    for i in range(0, len(new_chunks), batch_size):
        batch = new_chunks[i : i + batch_size]

        texts      = [c["text"]       for c in batch]
        ids        = [c["chunk_id"]   for c in batch]
        metadatas  = [
            {
                "source":       c["source"],
                "source_url":   c["source_url"],
                "topic":        c["topic"],
                "content_type": c["content_type"],
                "chunk_index":  c["chunk_index"],
                "total_chunks": c["total_chunks"],
            }
            for c in batch
        ]

        # Generate embeddings for this batch
        embeddings = model.encode(texts, show_progress_bar=False).tolist()

        # Upsert into ChromaDB
        # upsert: inserts new, updates existing — safe to re-run
        collection.upsert(
            ids        = ids,
            embeddings = embeddings,
            documents  = texts,
            metadatas  = metadatas,
        )

        total_stored += len(batch)
        print(f"  Stored batch {i // batch_size + 1} "
              f"({total_stored}/{len(new_chunks)} chunks)")

    print(f"\n✅ Vector store built: {collection.count()} total chunks in '{COLLECTION}'")
    print(f"   Persisted to: {os.path.abspath(persist_dir)}\n")


# ---------------------------------------------------------------------------
# Stage 4: Retrieval function
# ---------------------------------------------------------------------------

def retrieve(
    query: str,
    top_k: int                   = DEFAULT_TOP_K,
    filter_source: Optional[str] = None,
    filter_topic: Optional[str]  = None,
    model_name: str              = EMBED_MODEL,
    persist_dir: str             = CHROMA_DIR,
) -> list[dict]:
    """
    Embed a query and return the top-k most semantically similar chunks.

    Parameters
    ----------
    query         : plain-language question from the user
    top_k         : number of chunks to return (default 5)
                    - use 3-5 for simple conceptual questions
                    - use 8-10 for complex multi-step mechanism questions
    filter_source : optional — restrict to a specific source
                    e.g. "libretexts" | "stackexchange"
    filter_topic  : optional — restrict to a specific topic
                    e.g. "SN1/SN2/E1/E2" | "stereochemistry"
    model_name    : must match the model used at build time
    persist_dir   : path to the ChromaDB persistence directory

    Returns
    -------
    List of dicts, each containing:
        text         : chunk text
        source       : source name
        source_url   : original URL
        topic        : inferred topic
        content_type : "conceptual" | "study_strategy"
        chunk_index  : position in original document
        distance     : cosine distance (lower = more similar)
    """
    model      = load_embedding_model(model_name)
    collection, _ = get_chroma_collection(persist_dir)

    # Build optional metadata filter for ChromaDB
    # ChromaDB uses a dict-based where clause for metadata filtering
    where: Optional[dict] = None
    if filter_source and filter_topic:
        where = {"$and": [
            {"source": {"$eq": filter_source}},
            {"topic":  {"$eq": filter_topic}},
        ]}
    elif filter_source:
        where = {"source": {"$eq": filter_source}}
    elif filter_topic:
        where = {"topic": {"$eq": filter_topic}}

    # Embed the query using the same model as at ingestion time
    query_embedding = model.encode(query).tolist()

    # Query ChromaDB for top-k nearest neighbours
    results = collection.query(
        query_embeddings = [query_embedding],
        n_results        = top_k,
        where            = where,
        include          = ["documents", "metadatas", "distances"],
    )

    # Flatten ChromaDB's nested result structure into a clean list
    # ChromaDB returns lists-of-lists because it supports batch queries
    chunks_out = []
    for text, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        chunks_out.append({
            "text":         text,
            "source":       meta.get("source", "unknown"),
            "source_url":   meta.get("source_url", ""),
            "topic":        meta.get("topic", "general"),
            "content_type": meta.get("content_type", "conceptual"),
            "chunk_index":  meta.get("chunk_index", 0),
            "distance":     round(dist, 4),
        })

    return chunks_out


# ---------------------------------------------------------------------------
# Display helper
# ---------------------------------------------------------------------------

SEPARATOR = "=" * 70

def display_results(query: str, results: list[dict]) -> None:
    """Pretty-print retrieval results for manual inspection."""
    print(f"\n{SEPARATOR}")
    print(f"  QUERY: {query}")
    print(f"  Top-{len(results)} results")
    print(SEPARATOR)

    for i, r in enumerate(results, start=1):
        dist = r["distance"]
        if dist < 0.3:
            relevance = "🟢 High"
        elif dist < 0.5:
            relevance = "🟡 Medium"
        else:
            relevance = "🔴 Low"

        print(f"\n  [{i}] {relevance} (distance: {r['distance']})")
        print(f"      Source  : {r['source']}")
        print(f"      Topic   : {r['topic']}")
        print(f"      URL     : {r['source_url'][:80]}")
        print(f"      Chunk   : {r['chunk_index'] + 1}")
        print()
        # Show first 300 chars of chunk text as preview
        preview = r["text"][:300].replace("\n", " ")
        print(f"      Preview : {preview}...")
        print()

    print(SEPARATOR)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Orgo RAG — Embed chunks and query the vector store"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--build",
        action="store_true",
        help="Embed all chunks from chunks.jsonl and load into ChromaDB",
    )
    group.add_argument(
        "--query",
        type=str,
        metavar="QUESTION",
        help='Query the vector store, e.g. --query "What is SN2?"',
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=DEFAULT_TOP_K,
        help=f"Number of chunks to retrieve (default: {DEFAULT_TOP_K})",
    )
    parser.add_argument(
        "--source",
        type=str,
        default=None,
        help='Filter by source, e.g. --source libretexts',
    )
    parser.add_argument(
        "--topic",
        type=str,
        default=None,
        help='Filter by topic, e.g. --topic "SN1/SN2/E1/E2"',
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.build:
        build_vector_store()
    else:
        results = retrieve(
            query         = args.query,
            top_k         = args.top_k,
            filter_source = args.source,
            filter_topic  = args.topic,
        )
        display_results(args.query, results)