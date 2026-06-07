# Project 1 Planning: The Unofficial Guide

> Write this document before you write any pipeline code.
> Your spec and architecture diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Update the Retrieval Approach and Chunking Strategy sections if you change your approach during implementation.
> Update this file before starting any stretch features.

---

## Domain

<!-- What domain did you choose? Why is this knowledge valuable and hard to find through official channels? -->
The domain I have chosen is organic chemistry. Reason being the struggle many students experience going from general chemistry concepts to organic chemistry. Using organic chemistry subreddit, Khan Academy and LibreText, I'm hoping that students will be able to find specific answers to their question and/or watch a tutorial to gain an understanding of a defined topic.

---

## Documents

<!-- List your specific sources: URLs, subreddit names, forum threads, or file descriptions.
     Aim for at least 10 sources that together cover different subtopics or perspectives within your domain. -->

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


---

## Chunking Strategy

<!-- How will you split documents into chunks?
     State your chunk size (in tokens or characters), overlap size, and explain why those
     numbers fit the structure of your documents.
     A review-heavy corpus warrants different chunking than a long FAQ. -->

**Chunk size:**

**Overlap:**

**Reasoning:**

---

## Retrieval Approach

<!-- Which embedding model are you using (e.g., all-MiniLM-L6-v2 via sentence-transformers)?
     How many chunks will you retrieve per query (top-k)?
     If you were deploying this for real users and cost wasn't a constraint, what tradeoffs
     would you weigh in choosing a different embedding model — context length, multilingual
     support, accuracy on domain-specific text, latency? -->

**Embedding model:**

**Top-k:**

**Production tradeoff reflection:**

---

## Evaluation Plan

<!-- List your 5 test questions with their expected correct answers.
     Questions should be specific enough that you can judge whether the system's response
     is right or wrong. "What are good dining halls?" is too vague.
     "What do students say about wait times at [dining hall name] during lunch?" is testable. -->

| # | Question | Expected answer |
|---|----------|-----------------|
| 1 | | |
| 2 | | |
| 3 | | |
| 4 | | |
| 5 | | |

---

## Anticipated Challenges

<!-- What could go wrong? Name at least two specific risks with reasoning.
     Consider: noisy or inconsistent documents, missing source attribution, off-topic
     retrieval, chunks that split key information across boundaries. -->

1.

2.

---

## Architecture

<!-- Draw a diagram of your pipeline showing the five stages:
     Document Ingestion → Chunking → Embedding + Vector Store → Retrieval → Generation
     Label each stage with the tool or library you're using.
     You can use ASCII art, a Mermaid diagram, or embed a sketch as an image.
     You'll use this diagram as context when prompting AI tools to implement each stage. -->

---

## AI Tool Plan

<!-- For each part of the pipeline below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, which requirements)
     - What you expect it to produce
     - How you'll verify the output matches your spec

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Chunking Strategy section and ask it to implement chunk_text()
     with my specified chunk size and overlap" is a plan. -->

**Milestone 3 — Ingestion and chunking:**

**Milestone 4 — Embedding and retrieval:**

**Milestone 5 — Generation and interface:**
