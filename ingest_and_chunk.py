"""
Unofficial Guide: Organic Chemistry RAG Pipeline
Stage 1 — Document Ingestion
Stage 2 — Chunking

Sources:
- Reddit (r/OrganicChemistry, r/premed, r/Mcat)
- Chemistry Stack Exchange
- LibreTexts Organic Chemistry
- Khan Academy Organic Chemistry
"""

import os
import time
import json
import re
import requests
from dataclasses import dataclass, asdict
from bs4 import BeautifulSoup


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Dynamic chunk size and overlap — override via environment variables or edit here
CHUNK_SIZE    = int(os.getenv("CHUNK_SIZE", 500))    # tokens (approx. words)
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 100)) # tokens

# Output file for all chunks
OUTPUT_FILE = "chunks.jsonl"

# BeautifulSoup parser
HTML_PARSER = "html.parser"

# Reddit public JSON API — no credentials required
# Uses the unauthenticated reddit.com/r/<subreddit>/top.json endpoint
REDDIT_USER_AGENT = "orgo-rag-bot/0.1 (educational project, no auth)"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Chunk:
    chunk_id:     str            # unique identifier
    source:       str            # e.g. "reddit", "libretexts", "stackexchange", "khanacademy"
    source_url:   str            # original URL
    topic:        str            # e.g. "SN1/SN2", "stereochemistry", "general"
    content_type: str            # "conceptual" | "study_strategy"
    text:         str            # chunk text
    chunk_index:  int            # position within the original document
    total_chunks: int            # total chunks from this document


# ---------------------------------------------------------------------------
# Utility: approximate token count (1 token ≈ 1 word for English)
# ---------------------------------------------------------------------------

def count_tokens(text: str) -> int:
    return len(text.split())


# ---------------------------------------------------------------------------
# Utility: infer topic from text
# ---------------------------------------------------------------------------

TOPIC_KEYWORDS = {
    "SN1/SN2/E1/E2":       ["sn1", "sn2", "e1", "e2", "substitution", "elimination",
                             "nucleophilic", "leaving group"],
    "stereochemistry":      ["stereochemistry", "enantiomer", "diastereomer", "chiral",
                             "r/s", "rs configuration", "optical", "racemic", "fischer"],
    "carbonyl chemistry":   ["carbonyl", "aldehyde", "ketone", "carboxylic", "ester",
                             "amide", "acyl", "nucleophilic addition"],
    "reaction mechanisms":  ["mechanism", "arrow pushing", "curved arrow", "intermediate",
                             "transition state", "carbocation", "carbanion", "radical"],
    "aromaticity":          ["aromatic", "benzene", "huckel", "resonance", "delocali"],
    "acids and bases":      ["pka", "acid", "base", "conjugate", "proton", "deproton"],
    "study strategy":       ["study", "memorize", "exam", "tips", "professor", "grade",
                             "orgo 1", "orgo 2", "survive", "advice", "premed", "mcat"],
}

def infer_topic(text: str) -> str:
    lower = text.lower()
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return topic
    return "general"


def infer_content_type(text: str, source: str) -> str:
    """Conceptual = explains chemistry; study_strategy = advice on learning."""
    if source in ("reddit", "premed_reddit", "mcat_reddit"):
        lower = text.lower()
        strategy_signals = ["study", "exam", "tips", "advice", "professor",
                            "grade", "survive", "premed", "mcat", "memorize"]
        if any(s in lower for s in strategy_signals):
            return "study_strategy"
    return "conceptual"


# ---------------------------------------------------------------------------
# Core chunking function (fixed-size with overlap, dynamic via config)
# ---------------------------------------------------------------------------

def chunk_text(
    text: str,
    source: str,
    source_url: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[dict]:
    """
    Split text into overlapping fixed-size chunks.
    chunk_size and overlap are token-approximate (word-based).
    Returns a list of Chunk dicts ready for serialisation.
    """
    words = text.split()
    chunks = []
    start = 0
    index = 0

    while start < len(words):
        end = start + chunk_size
        chunk_words = words[start:end]
        chunk_text_str = " ".join(chunk_words)

        topic        = infer_topic(chunk_text_str)
        content_type = infer_content_type(chunk_text_str, source)

        chunk = Chunk(
            chunk_id     = f"{source}_{index}_{hash(chunk_text_str) & 0xFFFFFF:06x}",
            source       = source,
            source_url   = source_url,
            topic        = topic,
            content_type = content_type,
            text         = chunk_text_str,
            chunk_index  = index,
            total_chunks = -1,   # filled in after all chunks are created
        )
        chunks.append(chunk)

        # Advance by (chunk_size - overlap) to create sliding window
        start += chunk_size - overlap
        index += 1

    # Back-fill total_chunks now that we know the final count
    for c in chunks:
        c.total_chunks = len(chunks)

    return [asdict(c) for c in chunks]


# ---------------------------------------------------------------------------
# Semantic chunking for Reddit/Stack Exchange
# (split on natural paragraph/comment boundaries first, then apply fixed chunking
#  on any segment that still exceeds chunk_size)
# ---------------------------------------------------------------------------

def semantic_chunk(
    text: str,
    source: str,
    source_url: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[dict]:
    """
    For student-generated content (Reddit, Stack Exchange):
    1. Split on paragraph / double-newline boundaries.
    2. If a segment is under chunk_size tokens, keep it as-is.
    3. If a segment exceeds chunk_size, fall back to fixed chunking with overlap.
    """
    # Split on blank lines or comment separators
    segments = re.split(r"\n{2,}", text.strip())
    all_chunks = []

    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue
        if count_tokens(seg) <= chunk_size:
            topic        = infer_topic(seg)
            content_type = infer_content_type(seg, source)
            idx = len(all_chunks)
            chunk = Chunk(
                chunk_id     = f"{source}_{idx}_{hash(seg) & 0xFFFFFF:06x}",
                source       = source,
                source_url   = source_url,
                topic        = topic,
                content_type = content_type,
                text         = seg,
                chunk_index  = idx,
                total_chunks = -1,
            )
            all_chunks.append(asdict(chunk))
        else:
            # Segment too long — apply fixed chunking with overlap
            sub_chunks = chunk_text(seg, source, source_url, chunk_size, overlap)
            # Re-index sub-chunks relative to the running total
            for sc in sub_chunks:
                sc["chunk_index"] = len(all_chunks)
                all_chunks.append(sc)

    for c in all_chunks:
        c["total_chunks"] = len(all_chunks)

    return all_chunks


# ---------------------------------------------------------------------------
# Stage 1: Ingestion helpers
# ---------------------------------------------------------------------------

# # -- Reddit --

# def fetch_reddit_posts(subreddit: str, limit: int = 25) -> list[dict]:
#     """
#     Fetch top posts from a subreddit using Reddit's public JSON API.
#     No credentials required — appends .json to the standard Reddit URL.
#     Browser-like headers are required; Reddit blocks requests that look automated.
#     """
#     url = f"https://www.reddit.com/r/{subreddit}/top.json"
#     headers = {
#         "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
#                            "AppleWebKit/537.36 (KHTML, like Gecko) "
#                            "Chrome/124.0.0.0 Safari/537.36",
#         "Accept":          "application/json, text/javascript, */*; q=0.01",
#         "Accept-Language": "en-US,en;q=0.9",
#         "Accept-Encoding": "gzip, deflate, br",
#         "Referer":         "https://www.reddit.com/",
#         "DNT":             "1",
#     }
#     params = {"t": "all", "limit": limit}
#     r = requests.get(url, headers=headers, params=params, timeout=10)
#     r.raise_for_status()
#     posts = []
#     for post in r.json()["data"]["children"]:
#         d = post["data"]
#         posts.append({
#             "title":    d.get("title", ""),
#             "selftext": d.get("selftext", ""),
#             "url":      f"https://reddit.com{d.get('permalink', '')}",
#             "score":    d.get("score", 0),
#         })
#     return posts


# def ingest_reddit(subreddit: str, label: str) -> list[dict]:
#     """Ingest top posts from a subreddit and chunk them semantically."""
#     print(f"  Fetching r/{subreddit} ...")
#     posts = fetch_reddit_posts(subreddit, limit=25)
#     all_chunks = []
#     for post in posts:
#         text = f"{post['title']}\n\n{post['selftext']}".strip()
#         if len(text) < 50:
#             continue
#         chunks = semantic_chunk(text, label, post["url"])
#         all_chunks.extend(chunks)
#         time.sleep(0.5)   # polite rate limiting
#     print(f"    → {len(all_chunks)} chunks from r/{subreddit}")
#     return all_chunks


# -- LibreTexts --

LIBRETEXTS_URLS = [
    # Nucleophilic substitution (SN1/SN2)
    "https://chem.libretexts.org/Bookshelves/Organic_Chemistry/"
    "Organic_Chemistry_(OpenStax)/11%3A_Reactions_of_Alkyl_Halides-_Nucleophilic_Substitutions_and_Eliminations/"
    "11.01%3A_The_Discovery_of_Nucleophilic_Substitution_Reactions",
    
    # SN1 vs SN2 direct comparison
    "https://chem.libretexts.org/Courses/Brevard_College/CHE_202%3A_Organic_Chemistry_II/"
    "04%3A_Substitution_and_Elimination_reactions/4.08%3A_Comparison_of_SN1_and_SN2_Reactions",
    
    # Stereochemistry
    "https://chem.libretexts.org/Bookshelves/Organic_Chemistry/"
    "Organic_Chemistry_(OpenStax)/05%3A_Stereochemistry_at_Tetrahedral_Centers",
    
    # Elimination reactions (E1/E2)
    "https://chem.libretexts.org/Bookshelves/Inorganic_Chemistry/"
    "Organometallic_Chemistry_(Evans)/04%3A_Fundamentals_of_Organometallic_Chemistry/4.01%3A_-Elimination_Reactions",

    
    # Nucleophiles and electrophiles — directly covers Query 3
    "https://chem.libretexts.org/Courses/Purdue/Chem_26505%3A_Organic_Chemistry_I_(Lipton)/"
    "Chapter_7._Reactivity_and_Electron_Movement/7.1_Nucleophiles_and_Electrophiles",
    
    # Carbocation stability and resonance — directly covers Query 2
    "https://chem.libretexts.org/Bookshelves/Organic_Chemistry/Organic_Chemistry_(Morsch_et_al.)/"
    "07%3A_Alkenes-_Structure_and_Reactivity/7.10%3A_Carbocation_Structure_and_Stability",
    
    # Resonance structures — supports carbocation and mechanism questions
    "https://chem.libretexts.org/Bookshelves/Organic_Chemistry/Map%3A_Organic_Chemistry_(Wade)_Complete_and_Semesters_I_and_II/"
    "Map%3A_Organic_Chemistry_I_(Wade)/01%3A_Introduction_and_Review/1.10%3A_Resonance"
    "https://chem.libretexts.org/Bookshelves/Organic_Chemistry/Book%3A_Organic_Chemistry_with_a_Biological_Emphasis_v2.0_(Soderberg)/"
    "02%3A_Introduction_to_Organic_Structure_and_Bonding_II/2.04%3A_Resonance",
]

def clean_latex(text: str) -> str:
    """
    Strip LaTeX/MathJax boilerplate injected by LibreTexts pages.
    Removes \\newcommand blocks, \\( ... \\) inline math definitions,
    and other non-readable math markup that pollutes chunk text.
    """
    # Remove \newcommand and \renewcommand definitions
    text = re.sub(r"\\(re)?newcommand\{[^}]*\}\{[^}]*\}", "", text)
    text = re.sub(r"\\(re)?newcommand\{[^}]*\}\[[^\]]*\]\{[^}]*\}", "", text)
    # Remove \( ... \) and \[ ... \] math blocks (greedy and non-greedy)
    text = re.sub(r"\\\(.*?\\\)", "", text, flags=re.DOTALL)
    text = re.sub(r"\\\[.*?\\\]", "", text, flags=re.DOTALL)
    # Remove \definecolor and \unicode directives
    text = re.sub(r"\\definecolor\{[^}]*\}\{[^}]*\}\{[^}]*\}", "", text)
    text = re.sub(r"\\unicode\[[^\]]*\]\{[^}]*\}", "", text)
    # Remove leftover backslash commands like \vec, \mathbf, \mathrm, \,
    text = re.sub(r"\\[a-zA-Z,;!]+(\{[^}]*\})*", "", text)
    # Remove orphaned LaTeX delimiters: \) \( \} \{ that survived earlier passes
    text = re.sub(r"\\[(){}\[\]]", "", text)
    # Remove bare curly braces left after command removal
    text = re.sub(r"[{}]", "", text)
    # Remove dollar-sign math spans $...$ and $$...$$
    text = re.sub(r"\$\$.*?\$\$", "", text, flags=re.DOTALL)
    text = re.sub(r"\$[^$\n]+\$", "", text)
    # Collapse excess whitespace and blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def fetch_page_text(url: str) -> str:
    """Scrape and clean main text content from a LibreTexts or similar page."""
    headers = {"User-Agent": "orgo-rag-bot/0.1 (educational project)"}
    r = requests.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, HTML_PARSER)
    # LibreTexts stores content in #content or article tags
    content = soup.find("div", {"id": "content"}) or soup.find("article")
    raw = content.get_text(separator="\n", strip=True) if content \
          else soup.get_text(separator="\n", strip=True)
    return clean_latex(raw)


def ingest_libretexts() -> list[dict]:
    """Ingest LibreTexts pages using fixed-size chunking with overlap."""
    all_chunks = []
    for url in LIBRETEXTS_URLS:
        print(f"  Fetching LibreTexts: {url[-60:]} ...")
        try:
            text = fetch_page_text(url)
            chunks = chunk_text(text, "libretexts", url)
            all_chunks.extend(chunks)
            print(f"    → {len(chunks)} chunks")
            time.sleep(1)
        except Exception as e:
            print(f"    ✗ Failed: {e}")
    return all_chunks


# -- Khan Academy --

KHAN_URLS = [
    "https://www.khanacademy.org/science/organic-chemistry/substitution-elimination-reactions",
    "https://www.khanacademy.org/science/organic-chemistry/stereochemistry-topic",
    "https://www.khanacademy.org/science/organic-chemistry/organic-structures/acid-base-review/v/organic-acid-base-mechanisms",
]

def ingest_khan_academy() -> list[dict]:
    """
    Ingest Khan Academy overview pages.
    Note: Khan Academy is JavaScript-heavy; this scrapes static meta content.
    For richer content, consider their API or pre-downloaded transcripts.
    """
    all_chunks = []
    headers = {"User-Agent": "orgo-rag-bot/0.1 (educational project)"}
    for url in KHAN_URLS:
        print(f"  Fetching Khan Academy: {url[-60:]} ...")
        try:
            r = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(r.text, HTML_PARSER)
            # Extract any server-rendered text (titles, descriptions, topic lists)
            text = " ".join(tag.get_text(" ", strip=True)
                            for tag in soup.find_all(["h1", "h2", "h3", "p", "li"]))
            if len(text) > 100:
                chunks = semantic_chunk(text, "khanacademy", url)
                all_chunks.extend(chunks)
                print(f"    → {len(chunks)} chunks")
            else:
                print("    ⚠ Little static content found (JS-rendered page)")
            time.sleep(1)
        except Exception as e:
            print(f"    ✗ Failed: {e}")
    return all_chunks


# -- Stack Exchange --

def ingest_stack_exchange(tag: str = "organic-chemistry", page_size: int = 30) -> list[dict]:
    """
    Fetch top-voted Q&A from Chemistry Stack Exchange via public API.
    Retrieves both the question body and the top accepted/highest-voted answer
    so chunks contain complete, answerable content rather than just a question title.
    No authentication required.
    """
    print(f"  Fetching Chemistry Stack Exchange tag: {tag} ...")

    # Step 1: fetch questions with bodies
    q_url = "https://api.stackexchange.com/2.3/questions"
    q_params = {
        "order":    "desc",
        "sort":     "votes",
        "tagged":   tag,
        "site":     "chemistry",
        "pagesize": page_size,
        "filter":   "withbody",
    }
    r = requests.get(q_url, params=q_params, timeout=15)
    r.raise_for_status()
    items = r.json().get("items", [])

    # Step 2: fetch answers for each question
    question_ids = [str(item["question_id"]) for item in items]
    answers_map: dict[int, str] = {}

    if question_ids:
        ids_str = ";".join(question_ids)
        a_url = f"https://api.stackexchange.com/2.3/questions/{ids_str}/answers"
        a_params = {
            "order":    "desc",
            "sort":     "votes",
            "site":     "chemistry",
            "pagesize": 100,
            "filter":   "withbody",
        }
        a_resp = requests.get(a_url, params=a_params, timeout=15)
        a_resp.raise_for_status()
        for answer in a_resp.json().get("items", []):
            qid = answer["question_id"]
            # Keep only the top-voted answer per question
            if qid not in answers_map:
                answers_map[qid] = BeautifulSoup(
                    answer.get("body", ""), HTML_PARSER
                ).get_text(" ", strip=True)
        time.sleep(0.5)

    # Step 3: combine Q + top answer into one chunk-able document
    all_chunks = []
    for item in items:
        q_text = BeautifulSoup(
            item.get("body", ""), HTML_PARSER
        ).get_text(" ", strip=True)
        title   = item.get("title", "")
        qid     = item["question_id"]
        src_url = item.get("link", "")

        answer_text = answers_map.get(qid, "")
        combined = f"Q: {title}\n\n{q_text}"
        if answer_text:
            combined += f"\n\nA: {answer_text}"

        chunks = semantic_chunk(combined, "stackexchange", src_url)
        all_chunks.extend(chunks)
        time.sleep(0.3)

    print(f"    → {len(all_chunks)} chunks from Stack Exchange")
    return all_chunks


# ---------------------------------------------------------------------------
# Stage 2: Save chunks to JSONL
# ---------------------------------------------------------------------------

def save_chunks(chunks: list[dict], output_file: str = OUTPUT_FILE) -> None:
    with open(output_file, "w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk) + "\n")
    print(f"\n✅ Saved {len(chunks)} chunks to {output_file}")


def load_chunks(output_file: str = OUTPUT_FILE) -> list[dict]:
    chunks = []
    with open(output_file, "r", encoding="utf-8") as f:
        for line in f:
            chunks.append(json.loads(line.strip()))
    return chunks


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_pipeline(
    chunk_size: int  = CHUNK_SIZE,
    overlap: int     = CHUNK_OVERLAP,
    output_file: str = OUTPUT_FILE,
) -> list[dict]:
    """
    Run the full ingestion + chunking pipeline.

    Override chunk size and overlap dynamically:
        run_pipeline(chunk_size=300, overlap=60)
    Or via environment variables before running:
        CHUNK_SIZE=300 CHUNK_OVERLAP=60 python ingest_and_chunk.py
    """
    print("=" * 60)
    print("Unofficial Guide — Organic Chemistry RAG Pipeline")
    print(f"Chunk size: {chunk_size} tokens | Overlap: {overlap} tokens")
    print("=" * 60)

    all_chunks: list[dict] = []

    # -- Reddit sources --
    # print("\n[1/4] Ingesting Reddit ...")
    # try:
    #     all_chunks += ingest_reddit("OrganicChemistry", "reddit")
    #     all_chunks += ingest_reddit("premed",           "premed_reddit")
    #     all_chunks += ingest_reddit("Mcat",             "mcat_reddit")
    # except Exception as e:
    #     print(f"  ✗ Reddit ingestion failed: {e}")

    # -- LibreTexts --
    print("\n[2/4] Ingesting LibreTexts ...")
    all_chunks += ingest_libretexts()

    # -- Khan Academy --
    print("\n[3/4] Ingesting Khan Academy ...")
    all_chunks += ingest_khan_academy()

    # -- Stack Exchange --
    print("\n[4/4] Ingesting Chemistry Stack Exchange ...")
    all_chunks += ingest_stack_exchange()

    # -- Summary --
    print("\n--- Ingestion Summary ---")
    source_counts: dict[str, int] = {}
    type_counts:   dict[str, int] = {}
    topic_counts:  dict[str, int] = {}
    for c in all_chunks:
        source_counts[c["source"]]       = source_counts.get(c["source"], 0) + 1
        type_counts[c["content_type"]]   = type_counts.get(c["content_type"], 0) + 1
        topic_counts[c["topic"]]         = topic_counts.get(c["topic"], 0) + 1

    print(f"Total chunks: {len(all_chunks)}")
    print("\nBy source:")
    for src, count in sorted(source_counts.items()):
        print(f"  {src:<20} {count}")
    print("\nBy content type:")
    for ct, count in sorted(type_counts.items()):
        print(f"  {ct:<20} {count}")
    print("\nBy topic (top 5):")
    for topic, count in sorted(topic_counts.items(), key=lambda x: -x[1])[:5]:
        print(f"  {topic:<30} {count}")

    save_chunks(all_chunks, output_file)
    return all_chunks


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run_pipeline()