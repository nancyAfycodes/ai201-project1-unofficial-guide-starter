# The Unofficial Guide — Project 1

> **How to use this template:**
> Complete each section *after* you've built and tested the corresponding part of your system.
> Do not write placeholder text — if a section isn't done yet, leave it blank and come back.
> Every section below is required for submission. One-liners will not receive full credit.

---

## Domain

<!-- What topic or category of knowledge does your system cover?
     Why is this knowledge valuable, and why is it hard to find through official channels?
     Example: "Student reviews of CS professors at [university] — useful because official
     course descriptions don't reflect teaching style, exam difficulty, or workload." -->
RAG system covers topic related to Organic Chemistry. Reason being the complexity involved in understanding reaction patterns based on the various kinds of reaction that is not covered full in General Chemistry. Using RAG, a student is able search and study for a specific topics. This system fills the gap by making high-quality,
student-relevant explanations from LibreTexts and Chemistry Stack Exchange searchable
through plain-language questions.
---

## Document Sources

<!-- List every source you collected documents from.
     Be specific: include URLs, subreddit names, forum thread titles, or file names.
     Aim for variety — sources that together cover different subtopics or perspectives. -->

| #  | Resource                                                        | Source Type       | URL                                                                                                                          |
| -- | --------------------------------------------------------------- | ----------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| 1  | r/OrganicChemistry — General mechanisms discussion              | Reddit            | [https://www.reddit.com/r/OrganicChemistry/](https://www.reddit.com/r/OrganicChemistry/)                                     |
| 2  | r/OrganicChemistry — SN1 vs SN2 vs E1 vs E2 threads             | Reddit            | [https://www.reddit.com/r/OrganicChemistry/](https://www.reddit.com/r/OrganicChemistry/)                                     |
| 3  | r/premed — "How did you survive organic chemistry?"             | Reddit            | [https://www.reddit.com/r/premed/](https://www.reddit.com/r/premed/)                                                         |
| 4  | r/Mcat — Organic chemistry strategy threads                     | Reddit            | [https://www.reddit.com/r/Mcat/](https://www.reddit.com/r/Mcat/)                                                             |
| 5  | Chemistry Stack Exchange — Resonance & carbocation stability    | Stack Exchange    | [https://chemistry.stackexchange.com/](https://chemistry.stackexchange.com/)                                                 |
| 6  | Chemistry Stack Exchange — R/S configuration in stereochemistry | Stack Exchange    | [https://chemistry.stackexchange.com/](https://chemistry.stackexchange.com/)                                                 |
| 7  | LibreTexts — Nucleophilic Substitution chapter                  | Open Educational  | [https://chem.libretexts.org/Bookshelves/Organic_Chemistry](https://chem.libretexts.org/Bookshelves/Organic_Chemistry)       |
| 8  | LibreTexts — Stereochemistry chapter                            | Open Educational  | [https://chem.libretexts.org/](https://chem.libretexts.org/)                                                                 |
| 9  | OpenStax Chemistry — Organic compounds overview                 | Open Educational  | [https://openstax.org/books/chemistry-2e/pages/1-introduction](https://openstax.org/books/chemistry-2e/pages/1-introduction) |
| 10 | Khan Academy — Substitution and Elimination                     | Open Educational  | [https://www.khanacademy.org/science/organic-chemistry](https://www.khanacademy.org/science/organic-chemistry)               |
| 11 | Orgo Made Easy — Community Notes and Videos                     | Community / Video | [https://www.youtube.com/c/OrgoMadeEasy](https://www.youtube.com/c/OrgoMadeEasy)                                             |
| 12 | r/OrganicChemistry Wiki & Sidebar Resources                     | Reddit Wiki       | [https://www.reddit.com/r/OrganicChemistry/wiki](https://www.reddit.com/r/OrganicChemistry/wiki)                             |

> **Note:** Reddit (sources 1–4) and Khan Academy were planned sources but could not be
> ingested due to Reddit's 403 bot-blocking policy and Khan Academy's JavaScript-rendered
> pages. As a result, all 118 chunks are `conceptual` content type. Study strategy content
> is a known gap and a target for a future iteration.

---

## Chunking Strategy

<!-- Describe your chunking approach with enough specificity that someone else could reproduce it.
     Include:
     - Chunk size (characters or tokens) and why that size fits your documents
     - Overlap size and why (or why not) you used overlap
     - Any preprocessing you did before chunking (e.g., stripping HTML, removing headers)
     - What your final chunk count was across all documents -->

**Chunk size:**
Chunk size: ~ 500 tokens

**Overlap:**
Overlap: ~ 100 tokens

**Why these choices fit your documents:**
Since organic chemistry (OChem) answers can range from one-liners to multiline paragraphs, I think a hybrid chunking strategy wii be the most effective. I think a chunk size of about 500 tokens with an overlap of about 100 tokens ensures that answers are not lost at retrieval time. Another strategy is to add metadata tagging per chunk to help in improving answer quality.
Organic chemistry answers range from one-liners ("SN2 reactions invert stereochemistry")
to multi-paragraph mechanism walkthroughs. A hybrid chunking strategy handles both cases:
Reddit and Stack Exchange posts are split semantically at paragraph and comment boundaries,
keeping each self-contained thought as its own chunk. LibreTexts pages use fixed-size
chunking with 100-token overlap to ensure that mechanism explanations spanning multiple
paragraphs are not lost at chunk boundaries. Metadata tagging (`source`, `topic`,
`content_type`, `chunk_index`) is applied to every chunk at creation time to support
filtered retrieval later (AI generated).

Preprocessing applied before chunking:
- LaTeX/MathJax boilerplate stripped from LibreTexts pages using regex (`clean_latex()`)
- Stack Exchange HTML tags removed using BeautifulSoup
- Question body and top-voted answer combined into a single document per SE question

**Final chunk count:**
118 chunks across 2 active sources (LibreTexts: 23, Stack Exchange: 95)
---

## Embedding Model

<!-- Name the embedding model you used and explain your choice.
     Then answer: if you were deploying this system for real users and cost wasn't a constraint,
     what tradeoffs would you weigh in choosing a different model?
     Consider: context length limits, multilingual support, accuracy on domain-specific text,
     latency, and local vs. API-hosted. -->

**Model used:**
Model: text-embedding-3-large, due its stronger performance on technical, domain-specific text and higher dimensional embeddings, which improve semantic similarity for nuanced OChem concepts like stereochemistry and reaction mechanisms. this was updated to `multi-qa-MiniLM-L6-cos-v1`(sentence-transformers, runs locally) to allow for the question- answer pairs. It runs entirely locally with no API key or rate limits, making it practical for development and testing. 

**Production tradeoff reflection:**
If deployed for real users, key tradeoffs in model selection would include:
- Latency vs. accuracy: text-embedding-3-large is slower than the small variant; 
  a high-traffic system may prefer the small model with reranking instead.
- Multilingual support: switching to multilingual-e5-large would better serve 
  non-English speaking students at the cost of some domain-specific accuracy.
- Context length: longer context models reduce the risk of truncating a full 
  mechanism explanation mid-chunk.
---

## Retrieval Approach

**Embedding model:** `multi-qa-MiniLM-L6-cos-v1`

**Vector store:** ChromaDB (persistent, on-disk at `chroma_db/`)

**Top-k:** Dynamic — K=3–5 for simple conceptual questions, K=8–10 for complex multi-step
mechanism questions. Default is K=5. Note: embeddings retrieve text only; mechanism
diagrams are represented through their text descriptions.

**Distance metric:** Cosine similarity (standard for sentence-transformer embeddings)

**Relevance thresholds observed:**
- 🟢 High relevance: distance < 0.30
- 🟡 Medium relevance: distance 0.30–0.50
- 🔴 Low relevance: distance > 0.50

---

## Grounded Generation

<!-- Explain how your system enforces grounding — how does it prevent the LLM from answering
     beyond the retrieved documents?
     Describe both your system prompt (what instruction you gave the model) and any structural
     choices (e.g., how you formatted the context, whether you filtered low-relevance chunks).
     Do not just say "I told it to use the documents" — show the actual instruction or explain
     the mechanism. -->

**System prompt grounding instruction:**
The system prompt explicitly prohibits the LLM from drawing on its training knowledge:

```
You are the Unofficial Organic Chemistry Guide — a helpful assistant that answers
student questions about organic chemistry concepts and study strategies.

STRICT GROUNDING RULES:
1. Answer ONLY using information from the provided document excerpts below.
2. Do NOT use your general training knowledge, even if you are confident in the answer.
3. If the provided excerpts do not contain enough information to answer the question,
   respond with exactly: "I don't have enough information on that in my current sources."
4. Do not speculate, infer, or extrapolate beyond what is explicitly stated in the excerpts.
5. Keep your answer clear and student-friendly — avoid unnecessary jargon.
```

The user message wraps each retrieved chunk in a labelled `[Excerpt N — SOURCE | TOPIC]`
block before appending the question, making it unambiguous what the model is allowed to
draw from. Temperature is set to 0.2 to keep generation close to the retrieved context.


**How source attribution is surfaced in the response:**
ource attribution is **programmatic, not LLM-generated**. After the LLM produces its
answer, `build_source_list()` constructs a deduplicated list of source URLs directly from
the retrieval metadata — the model never decides what to cite. This guarantees attribution
is always present and always accurate regardless of what the LLM outputs.
---

## Evaluation Report

<!-- Run your 5 test questions from planning.md through your system and record the results.
     Be honest — a partially accurate or inaccurate result that you explain well is more
     valuable than a suspiciously perfect result. -->

| # | Question | Expected Answer | System Response (summarized) | Retrieval Quality | Response Accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | What is the difference between SN1 and SN2 reaction mechanisms? | SN1 is two-step via carbocation intermediate, favored by tertiary substrates and polar protic solvents. SN2 is concerted with backside attack, favored by primary substrates and polar aprotic solvents. | Correctly explained SN1 proceeds through a carbocation intermediate with racemization, while SN2 is concerted with inversion of configuration. Solvent and substrate effects included. | Partially relevant — best chunk was SE question about sp2 centres, not a direct comparison. LibreTexts SN1/SN2 comparison page retrieved in positions 2–3. | Partially accurate — mechanism contrast correct but solvent effects were thin. |
| 2 | How does resonance stabilization affect carbocation stability? | Greater resonance delocalization stabilizes carbocations more. Allylic and benzylic carbocations are especially stable due to pi system delocalization. | Correctly described charge delocalization in benzylic carbocations with three additional resonance structures on the aromatic ring. Mentioned cyclopropylmethyl carbocation stability. | Relevant — 4 of 5 retrieved chunks were 🟡 Medium relevance directly about carbocation stability. | Accurate — answer matched expected content closely. |
| 3 | What is the difference between a nucleophile and an electrophile in organic chemistry? | Nucleophile is electron-rich, donates electrons to form a bond. Electrophile is electron-poor, accepts electrons. | Correctly defined nucleophile as an electron-rich atom that donates a pair of electrons to form a new covalent bond, and electrophile as an electron-poor atom that is an attractive target for nucleophiles. Noted that in most nucleophilic substitution reactions the electrophilic atom is a carbon bonded to an electronegative atom. Summarized in plain language: "a nucleophile is a species that donates electrons, while an electrophile is a species that accepts electrons." | Relevant — dedicated LibreTexts nucleophiles/electrophiles page retrieved as top result (distance 0.37). Source correctly attributed as LibreTexts (SN1/SN2/E1/E2) programmatically. | Accurate — best-performing query. Answer grounded entirely in retrieved excerpts. |
| 4 | What factors determine whether E1 or E2 elimination will occur? | E1 favored by tertiary substrates, weak bases, polar protic solvents. E2 favored by strong bulky bases and requires anti-periplanar geometry. | Partially addressed — described elimination in context of organometallic beta-elimination. Did not clearly distinguish E1 vs E2 base strength requirements. | Partially relevant — elimination chunks retrieved but from organometallic source rather than a direct E1/E2 comparison page. | Partially accurate — elimination concept correct but E1/E2 distinction was not clearly drawn. |
| 5 | What do students say is the hardest topic in Orgo 1 and how did they get through it? | Students commonly cite stereochemistry as hardest. Strategies include molecular models, Fischer projections, spaced repetition. | "I don't have enough information on that in my current sources." — system correctly refused rather than hallucinating. | Off-target — no study strategy chunks exist in corpus; all 118 chunks are conceptual. | Inaccurate — system correctly identified its own gap rather than fabricating an answer. |

**Retrieval quality:** Relevant / Partially relevant / Off-target  
**Response accuracy:** Accurate / Partially accurate / Inaccurate

---

## Stretch Feature: Metadata Filtering

Metadata filtering was implemented as an extra credit stretch feature. The retrieval
layer already supported `filter_source` and `filter_topic` parameters — this feature
wired those parameters into the Gradio interface via two dropdown menus.

**How it works:**
Every chunk stored in ChromaDB carries metadata tags assigned at ingestion time:
`source` (e.g. `libretexts`, `stackexchange`) and `topic` (e.g. `SN1/SN2/E1/E2`,
`stereochemistry`, `reaction mechanisms`). The filter dropdowns pass these directly
into ChromaDB's `where` clause, restricting the vector search to matching chunks before
distance scoring occurs. Selecting `"All"` applies no filter and searches the full corpus.

**Interface additions:**
A collapsible `🔎 Filter by Source or Topic` accordion was added below the top-k slider,
containing two dropdowns. It is collapsed by default to keep the main interface clean
for users who do not need filtering.

**Example filter combinations and their use cases:**

| Source Filter | Topic Filter | Use Case |
|---|---|---|
| All | SN1/SN2/E1/E2 | Focus retrieval on substitution/elimination only |
| libretexts | All | Textbook-only answers — avoids Q&A community content |
| stackexchange | reaction mechanisms | Community explanations of mechanism questions only |
| libretexts | stereochemistry | Textbook coverage of chirality and R/S configuration |

**Observed benefit:**
Filtering by `topic: SN1/SN2/E1/E2` on the nucleophile/electrophile query reduced
noise from unrelated chunks and kept retrieved context tightly scoped to substitution
reaction content, which improved the coherence of the generated answer.

---

## Failure Case Analysis

<!-- Identify at least one question where retrieval or generation did not work as expected.
     Write a specific explanation of *why* it failed, tied to a part of the pipeline.

     "The answer was wrong" is not an explanation.

     "The relevant information was split across a chunk boundary, so retrieval returned
     only half the context — the model didn't have enough to answer correctly" is an explanation.

     "The embedding model treated the professor's nickname as out-of-vocabulary and returned
     results from an unrelated review" is an explanation. -->

**Question that failed:**
**Question that failed:**
*"What do students say is the hardest topic in Orgo 1 and how did they get through it?"*

**What the system returned:**
"I don't have enough information on that in my current sources." — the system correctly
refused to answer rather than hallucinating.

**Root cause (tied to a specific pipeline stage):**
This is a **Stage 1 (Ingestion) failure**, not a retrieval or generation failure. The
original domain plan included Reddit (r/OrganicChemistry, r/premed, r/Mcat) as the primary
source for student experience and study strategy content. All three subreddits were blocked
at ingestion time with a 403 error due to Reddit's bot-blocking policy introduced in 2023.
Khan Academy, the other planned study-strategy source, serves pages via JavaScript rendering
which the scraper cannot access. As a result, 100% of the 118 ingested chunks are
`conceptual` content from LibreTexts and Stack Exchange — the corpus has no coverage of
the study strategy half of the domain. The embedding model retrieves the least dissimilar
chunks it can find, but when no relevant chunks exist, the grounding instruction correctly
prevents the model from substituting its own knowledge.

**What you would change to fix it:**
The most direct fix is to replace Reddit scraping with the **Pushshift API** or a
pre-downloaded Reddit dataset (e.g. from Academic Torrents), which bypass the 403 block.
Alternatively, student forum posts from platforms like **Discord servers** for orgo courses
or **College Confidential** threads could be manually exported and added to the corpus.
A secondary fix would be to detect when all retrieved chunks are below a relevance
threshold and warn the user that the question may be outside the system's current coverage,
rather than silently returning the fallback message.

---
## Anticipated Challenges vs. Reality
| Challenge Anticipated | Did It Occur? | Notes |
|---|---|---|
| Visual/diagram content hard to represent as text | Partially | Mechanism descriptions retrieved as text — worked better than expected |
| Terminology mismatch (student vs. formal) | Yes | Queries like "fish hook arrow" would likely fail; formal terms worked well |
| Source quality variance | Not applicable | Reddit blocked; all sources were vetted educational content |
| Chunk boundary splits | Yes | Mid-sentence chunks flagged by inspector; overlap mitigated impact |
| Outdated/course-specific info | No | LibreTexts content is current and curriculum-agnostic |
| Multi-hop questions | Yes | E1/E2 question required connecting substrate, base, and solvent — single retrieval pass insufficient |
| Overconfident generation | No | Grounding rules and low temperature (0.2) kept model conservative |

---

## Spec Reflection

<!-- Reflect on how planning.md shaped your implementation.
     Answer both questions with at least 2–3 sentences each. -->

**One way the spec helped you during implementation:**
The chunking strategy section of planning.md forced an early decision about hybrid
chunking before any code was written. Having already committed to semantic chunking for
Reddit/Stack Exchange and fixed-size chunking for LibreTexts meant the ingestion code
had a clear architecture from the start rather than being written ad hoc. The metadata
tagging plan (source, topic, content_type) also paid off directly in the retrieval stage —
being able to filter by source and topic during testing made it much easier to diagnose
why certain queries were failing.

**One way your implementation diverged from the spec, and why:**
The spec called for `text-embedding-3-large` as the embedding model, but the implementation
switched to `multi-qa-MiniLM-L6-cos-v1` after initial retrieval results showed poor
distance scores across all queries. The original model was chosen for its dimensional
strength on technical text, but it is a general-purpose model not optimized for
question-to-passage matching. The Q&A-trained model produced meaningfully better distances
on conceptual questions (0.37–0.44 vs 0.64–0.78) and runs locally with no API dependency.
This was a spec divergence driven by empirical testing rather than up-front planning.

---

## AI Usage

<!-- Describe at least 2 specific instances where you used an AI tool during this project.
     For each: what did you give the AI as input, what did it produce, and what did you
     change, override, or direct differently?

     "I used Claude to help me code" is not sufficient.
     "I gave Claude my Chunking Strategy section from planning.md and asked it to implement
     chunk_text(). It returned a function using a fixed character split. I overrode the
     chunk size from 500 to 200 because my documents are short reviews, not long guides." -->

**Instance 1**

- *What I gave the AI:* The chunking strategy section from planning.md, the list of source
  URLs, the Chunk dataclass fields (chunk_id, source, source_url, topic, content_type,
  text, chunk_index, total_chunks), and a request to implement the full ingestion and
  chunking pipeline.
- *What it produced:* A complete `ingest_and_chunk.py` with Reddit OAuth ingestion,
  LibreTexts scraping, Khan Academy scraping, Stack Exchange API ingestion, fixed-size
  chunking with overlap, semantic chunking for student-generated content, and metadata
  tagging per chunk.
- *What I changed or overrode:* Reddit OAuth failed with a 401 error and was replaced with
  the public `.json` API (which was subsequently blocked with a 403). LibreTexts URLs
  required manual correction three times as the generated URLs returned 404 errors.
  The `clean_latex()` function required two iterations to catch all residual MathJax
  patterns (`\,}\)` and `$...$` spans). Stack Exchange ingestion was upgraded to also
  fetch top answer bodies after the inspector revealed chunks contained only 12-word
  question titles.

**Instance 2**

- *What I gave the AI:* The retrieval approach section from planning.md, the pipeline
  diagram, the `retrieve()` function signature from `embed_and_retrieve.py`, the grounding
  requirement (answers from retrieved context only), and a request to implement generation
  and a Gradio interface.
- *What it produced:* A complete `generate_and_interface.py` with a strict system prompt,
  numbered context blocks in the user message, programmatic source attribution via
  `build_source_list()`, a Gradio Blocks interface with a top-k slider, example queries
  from the evaluation plan, and a retrieved chunks transparency accordion.
- *What I changed or overrode:* The `gr.themes.Soft()` and `title` parameters caused
  deprecation warnings and then a `TypeError` across two Gradio versions. These were
  resolved by moving `theme` back to `Blocks()` and removing `title` entirely. The
  embedding model was also switched from `all-MiniLM-L6-v2` to `multi-qa-MiniLM-L6-cos-v1`
  after retrieval testing revealed poor distance scores, requiring a full vector store
  rebuild with a new collection name to avoid stale embeddings.