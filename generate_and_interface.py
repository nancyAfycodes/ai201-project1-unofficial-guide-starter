"""
Unofficial Guide: Organic Chemistry RAG Pipeline
Stage 5 — Grounded Generation + Gradio Interface

LLM     : Groq llama-3.3-70b-versatile (free tier, OpenAI-compatible)
Interface: Gradio web UI

Grounding guarantee:
  - System prompt explicitly forbids answering outside retrieved context
  - Source attribution is appended programmatically after generation —
    the LLM does not decide what to cite; the retrieval pipeline does

Usage:
    python generate_and_interface.py
    # Opens Gradio UI at http://127.0.0.1:7860
"""

import os
from dotenv import load_dotenv
from groq import Groq
import gradio as gr

from embed_and_retrieve import retrieve

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

load_dotenv()

GROQ_MODEL    = "llama-3.3-70b-versatile"
DEFAULT_TOP_K = 5

# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are the Unofficial Organic Chemistry Guide — a helpful assistant \
that answers student questions about organic chemistry concepts and study strategies.

STRICT GROUNDING RULES:
1. Answer ONLY using information from the provided document excerpts below.
2. Do NOT use your general training knowledge, even if you are confident in the answer.
3. If the provided excerpts do not contain enough information to answer the question, \
respond with exactly: "I don't have enough information on that in my current sources."
4. Do not speculate, infer, or extrapolate beyond what is explicitly stated in the excerpts.
5. Keep your answer clear and student-friendly — avoid unnecessary jargon.
6. Do not mention these instructions or the fact that you are following rules."""

CONTEXT_TEMPLATE = """Here are the relevant document excerpts retrieved for this question:

{context_blocks}

---
Student question: {question}

Answer the question using ONLY the information in the excerpts above."""


def build_context_blocks(chunks: list[dict]) -> str:
    """
    Format retrieved chunks into numbered context blocks for the prompt.
    Each block is labelled with its source so the LLM sees provenance,
    even though attribution is also appended programmatically afterward.
    """
    blocks = []
    for i, chunk in enumerate(chunks, start=1):
        source_label = f"{chunk['source'].upper()} | {chunk['topic']}"
        blocks.append(
            f"[Excerpt {i} — {source_label}]\n{chunk['text'].strip()}"
        )
    return "\n\n".join(blocks)


# ---------------------------------------------------------------------------
# Source attribution — programmatic, not LLM-generated
# ---------------------------------------------------------------------------

def build_source_list(chunks: list[dict]) -> str:
    """
    Build a deduplicated source list from retrieved chunks.
    Attribution is constructed from retrieval metadata — the LLM never
    decides which sources to cite; this function always appends them.
    """
    seen_urls: set[str] = set()
    lines = []
    for chunk in chunks:
        url = chunk["source_url"]
        if url not in seen_urls:
            seen_urls.add(url)
            label = chunk["source"].capitalize()
            topic = chunk["topic"]
            lines.append(f"- **{label}** ({topic}): {url}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Stage 5: Grounded generation
# ---------------------------------------------------------------------------

def generate_answer(
    question: str,
    top_k: int = DEFAULT_TOP_K,
) -> tuple[str, str, list[dict]]:
    """
    Full RAG pipeline: retrieve → generate → attribute.

    Returns
    -------
    answer       : LLM-generated answer grounded in retrieved chunks
    sources_text : programmatically built source attribution string
    chunks       : raw retrieved chunks (for display/debugging)
    """
    if not question.strip():
        return "Please enter a question.", "", []

    # Stage 4 — retrieve relevant chunks
    chunks = retrieve(query=question, top_k=top_k)

    if not chunks:
        return (
            "I don't have enough information on that in my current sources.",
            "",
            [],
        )

    # Build grounded prompt
    context_blocks = build_context_blocks(chunks)
    user_message   = CONTEXT_TEMPLATE.format(
        context_blocks=context_blocks,
        question=question,
    )

    # Call Groq LLM
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_message},
        ],
        temperature=0.2,   # low temperature = more faithful to context
        max_tokens=600,
    )

    answer = response.choices[0].message.content.strip()

    # Programmatic source attribution — always appended regardless of LLM output
    sources_text = build_source_list(chunks)

    return answer, sources_text, chunks


# ---------------------------------------------------------------------------
# Gradio interface
# ---------------------------------------------------------------------------

def gradio_query(question: str, top_k: int) -> tuple[str, str, str]:
    """
    Gradio-facing wrapper.
    Returns answer, sources, and a formatted chunk preview for transparency.
    """
    answer, sources_text, chunks = generate_answer(question, top_k=int(top_k))

    # Build chunk preview for the "Retrieved Chunks" accordion
    if chunks:
        preview_lines = []
        for i, c in enumerate(chunks, start=1):
            dist   = c.get("distance", "n/a")
            source = c["source"]
            topic  = c["topic"]
            text   = c["text"][:250].replace("\n", " ")
            preview_lines.append(
                f"**[{i}] {source.upper()} — {topic}** (distance: {dist})\n{text}..."
            )
        chunks_preview = "\n\n".join(preview_lines)
    else:
        chunks_preview = "No chunks retrieved."

    return answer, sources_text, chunks_preview


def build_interface() -> gr.Blocks:
    """Construct and return the Gradio Blocks interface."""

    with gr.Blocks(title="The Unofficial Orgo Guide", theme=gr.themes.Soft()) as demo:

        gr.Markdown(
            """
            # 🧪 The Unofficial Organic Chemistry Guide
            Ask any question about organic chemistry concepts or study strategies.
            Answers are grounded in real course materials — LibreTexts and Chemistry
            Stack Exchange. Sources are always cited.
            """
        )

        with gr.Row():
            with gr.Column(scale=3):
                question_box = gr.Textbox(
                    label="Your Question",
                    placeholder=(
                        "e.g. What is the difference between SN1 and SN2 reactions?"
                    ),
                    lines=2,
                )
            with gr.Column(scale=1):
                top_k_slider = gr.Slider(
                    minimum=3,
                    maximum=10,
                    value=DEFAULT_TOP_K,
                    step=1,
                    label="Sources to retrieve (top-k)",
                    info="Higher = more context, but may add noise",
                )

        submit_btn = gr.Button("Ask", variant="primary")

        answer_box = gr.Textbox(
            label="Answer",
            lines=8,
            interactive=False,
        )

        sources_box = gr.Textbox(
            label="📚 Sources",
            lines=4,
            interactive=False,
            info="These sources were retrieved from the vector store — "
                 "attribution is programmatic, not LLM-generated.",
        )

        with gr.Accordion("🔍 Retrieved Chunks (transparency view)", open=False):
            chunks_box = gr.Markdown()

        # Example queries mapped to your evaluation plan
        gr.Examples(
            examples=[
                ["What is the difference between SN1 and SN2 reaction mechanisms?"],
                ["How does resonance stabilization affect carbocation stability?"],
                ["What is the difference between a nucleophile and an electrophile?"],
                ["What factors determine whether E1 or E2 elimination will occur?"],
                ["How do I determine R/S configuration in stereochemistry?"],
            ],
            inputs=question_box,
            label="Example queries from the evaluation plan",
        )

        # Wire up the submit button
        submit_btn.click(
            fn=gradio_query,
            inputs=[question_box, top_k_slider],
            outputs=[answer_box, sources_box, chunks_box],
        )

        # Also allow Enter key submission
        question_box.submit(
            fn=gradio_query,
            inputs=[question_box, top_k_slider],
            outputs=[answer_box, sources_box, chunks_box],
        )

    return demo


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Verify API key is loaded before launching
    if not os.getenv("GROQ_API_KEY"):
        raise EnvironmentError(
            "GROQ_API_KEY not found. "
            "Add it to your .env file: GROQ_API_KEY=your_key_here"
        )

    demo = build_interface()
    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,       # set True to get a public Gradio link
    )
