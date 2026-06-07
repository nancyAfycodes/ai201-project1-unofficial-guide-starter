"""
Unofficial Guide: Organic Chemistry RAG Pipeline
Chunk Inspection Script

Loads chunks.jsonl and prints 5 representative chunks across
different sources, topics, and content types for manual review.

For each chunk, answer:
  1. Does this chunk make sense on its own?
  2. Could someone answer a question from this chunk alone?
"""

import json
import textwrap
from collections import defaultdict

CHUNKS_FILE  = "chunks.jsonl"
DISPLAY_WIDTH = 80


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------

def load_chunks(path: str = CHUNKS_FILE) -> list[dict]:
    chunks = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                chunks.append(json.loads(line))
    return chunks


# ---------------------------------------------------------------------------
# Selection: pick 5 representative chunks
# Covers different sources and content types so the sample is diverse
# ---------------------------------------------------------------------------

TARGET_PROFILES = [
    {"source": "reddit",        "content_type": "study_strategy"},
    {"source": "libretexts",    "content_type": "conceptual"},
    {"source": "stackexchange", "content_type": "conceptual"},
    {"source": "khanacademy",   "content_type": "conceptual"},
    {"source": "premed_reddit", "content_type": "study_strategy"},
]

def select_representative(chunks: list[dict]) -> list[dict]:
    """
    Pick one chunk per target profile.
    Falls back to any chunk from that source if the content_type doesn't match.
    Falls back to any unselected chunk if the source isn't present.
    """
    # Index chunks by source
    by_source: dict[str, list[dict]] = defaultdict(list)
    for c in chunks:
        by_source[c["source"]].append(c)

    selected = []
    used_ids = set()

    for profile in TARGET_PROFILES:
        pool = by_source.get(profile["source"], [])

        # Prefer matching content_type, then any from that source
        match = next(
            (c for c in pool
             if c["content_type"] == profile["content_type"]
             and c["chunk_id"] not in used_ids),
            None
        ) or next(
            (c for c in pool if c["chunk_id"] not in used_ids),
            None
        )

        # Final fallback: any unused chunk from the whole corpus
        if match is None:
            match = next(
                (c for c in chunks if c["chunk_id"] not in used_ids),
                None
            )

        if match:
            selected.append(match)
            used_ids.add(match["chunk_id"])

    return selected


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

SEPARATOR = "=" * DISPLAY_WIDTH

def fmt_meta(chunk: dict) -> str:
    return (
        f"  Source       : {chunk['source']}\n"
        f"  Content type : {chunk['content_type']}\n"
        f"  Topic        : {chunk['topic']}\n"
        f"  Chunk        : {chunk['chunk_index'] + 1} of {chunk['total_chunks']}\n"
        f"  URL          : {chunk['source_url']}\n"
        f"  Chunk ID     : {chunk['chunk_id']}"
    )


def fmt_text(text: str, width: int = DISPLAY_WIDTH - 2) -> str:
    """Wrap text to width, indented by 2 spaces."""
    paragraphs = text.split("\n")
    wrapped = []
    for para in paragraphs:
        if para.strip():
            wrapped.append(
                textwrap.fill(para.strip(), width=width,
                              initial_indent="  ", subsequent_indent="  ")
            )
    return "\n".join(wrapped)


def self_contained_score(chunk: dict) -> str:
    """
    Heuristic self-containment check.
    Flags chunks that may be hard to understand in isolation.
    """
    text  = chunk["text"].lower()
    flags = []

    # Starts mid-sentence (likely a boundary split)
    first_word = chunk["text"].split()[0] if chunk["text"].split() else ""
    if first_word and first_word[0].islower():
        flags.append("⚠  Starts mid-sentence — may be missing context")

    # Very short chunks
    word_count = len(chunk["text"].split())
    if word_count < 30:
        flags.append(f"⚠  Very short ({word_count} words) — may lack enough context")

    # Dangling pronouns with no referent
    dangling = ["it does", "this means", "as mentioned", "see above",
                "the above", "the following", "as shown"]
    found = [d for d in dangling if d in text]
    if found:
        flags.append(f"⚠  Possible dangling reference: '{found[0]}'")

    # Mid-document chunk (not first or last)
    if chunk["chunk_index"] > 0 and chunk["chunk_index"] < chunk["total_chunks"] - 1:
        flags.append("ℹ  Mid-document chunk — overlap should preserve boundary context")

    if not flags:
        return "  ✅ Appears self-contained"
    return "\n".join(f"  {f}" for f in flags)


def print_chunk(n: int, chunk: dict) -> None:
    print(f"\n{SEPARATOR}")
    print(f"  CHUNK {n} OF 5")
    print(SEPARATOR)
    print(fmt_meta(chunk))
    print()
    print("  --- Text ---")
    print(fmt_text(chunk["text"]))
    print()
    print("  --- Self-containment check ---")
    print(self_contained_score(chunk))
    print()
    print("  --- Manual review questions ---")
    print("  1. Does this chunk make sense on its own?          [ Yes / No / Partially ]")
    print("  2. Could a question be answered from this alone?   [ Yes / No / Partially ]")
    print("  3. Is the topic tag accurate?                      [ Yes / No ]")
    print("  4. Is the content_type tag accurate?               [ Yes / No ]")


# ---------------------------------------------------------------------------
# Summary stats
# ---------------------------------------------------------------------------

def print_summary(chunks: list[dict]) -> None:
    print(f"\n{SEPARATOR}")
    print("  CORPUS SUMMARY")
    print(SEPARATOR)

    source_counts:  dict[str, int] = defaultdict(int)
    type_counts:    dict[str, int] = defaultdict(int)
    topic_counts:   dict[str, int] = defaultdict(int)
    word_counts:    list[int]      = []

    for c in chunks:
        source_counts[c["source"]]     += 1
        type_counts[c["content_type"]] += 1
        topic_counts[c["topic"]]       += 1
        word_counts.append(len(c["text"].split()))

    avg_words = sum(word_counts) / len(word_counts) if word_counts else 0
    min_words = min(word_counts) if word_counts else 0
    max_words = max(word_counts) if word_counts else 0

    print(f"  Total chunks : {len(chunks)}")
    print(f"  Avg length   : {avg_words:.0f} words")
    print(f"  Min / Max    : {min_words} / {max_words} words")

    print("\n  By source:")
    for src, count in sorted(source_counts.items()):
        bar = "█" * (count // 2)
        print(f"    {src:<20} {count:>4}  {bar}")

    print("\n  By content type:")
    for ct, count in sorted(type_counts.items()):
        print(f"    {ct:<20} {count:>4}")

    print("\n  By topic:")
    for topic, count in sorted(topic_counts.items(), key=lambda x: -x[1]):
        print(f"    {topic:<30} {count:>4}")

    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def inspect(path: str = CHUNKS_FILE) -> None:
    print(f"\nLoading chunks from '{path}' ...")
    try:
        chunks = load_chunks(path)
    except FileNotFoundError:
        print(f"\n❌ '{path}' not found.")
        print("   Run ingest_and_chunk.py first to generate the chunks file.")
        return

    print(f"Loaded {len(chunks)} chunks.\n")

    print_summary(chunks)

    sample = select_representative(chunks)

    print(f"{SEPARATOR}")
    print("  REPRESENTATIVE SAMPLE (5 chunks)")
    print(f"{SEPARATOR}")

    for i, chunk in enumerate(sample, start=1):
        print_chunk(i, chunk)

    print(f"\n{SEPARATOR}")
    print("  INSPECTION COMPLETE")
    print(f"{SEPARATOR}\n")


if __name__ == "__main__":
    inspect()
