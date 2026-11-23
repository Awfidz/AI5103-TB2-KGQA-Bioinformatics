"""Streamlit GUI for the drug-discovery KGQA application.

Run from the repository root:
    .venv\\Scripts\\streamlit run kgqa\\app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kgqa.config import get_settings  # noqa: E402
from kgqa.kg import KGError, get_kg  # noqa: E402
from kgqa.linker import EntityLinker  # noqa: E402
from kgqa.llm import OllamaClient  # noqa: E402
from kgqa.pipeline import KGQA, QAResult  # noqa: E402

EXAMPLE_QUESTIONS = [
    "Lembaga regulator apa saja yang telah menyetujui sildenafil, beserta tanggal persetujuannya?",
    "Is ciprofloxacin indicated for typhoid fever, contraindicated in epilepsy, and does it have a strong "
    "adverse signal for tendon pain?",
    "Apakah trastuzumab tergolong obat berizin dengan risiko keamanan tinggi?",
    "Which Reactome pathways are affected by imatinib's mechanism of action?",
    "Obat apa saja yang dikontraindikasikan pada pasien dengan Hepatic failure?",
    "What are the three strongest adverse event signals for diazepam?",
]

st.set_page_config(page_title="Drug KGQA", page_icon="💊", layout="wide")


@st.cache_resource(show_spinner="Loading knowledge graph...")
def load_kg(backend: str):
    settings = get_settings()
    settings.kg_backend = backend
    kg = get_kg(settings)
    return kg, EntityLinker(kg), kg.triple_count()


def render_result(res: QAResult) -> None:
    if res.error:
        st.error(res.error)
    if res.answer:
        st.markdown(res.answer)

    if res.result is not None and len(res.result):
        with st.expander(f"Results from the knowledge graph ({len(res.result)} rows)", expanded=False):
            st.dataframe(res.result.as_text_rows(), width="stretch", hide_index=True)
    if res.sparql:
        with st.expander("Generated SPARQL", expanded=res.result is None):
            st.code(res.sparql, language="sparql")
    with st.expander("How the answer was produced"):
        if res.entities:
            st.markdown("**Entities found in the question**")
            st.markdown("\n".join(
                f"- `{m.entity.label}` ({m.entity.cls}, score {m.score:.2f})" for m in res.entities
            ))
        else:
            st.markdown("No KG entities were recognised in the question.")
        st.markdown(f"**SPARQL attempts:** {len(res.attempts)}")
        for i, a in enumerate(res.attempts, 1):
            status = f"error: {a.error}" if a.error else f"{a.rows} row(s)"
            st.markdown(f"{i}. {status}")
            if len(res.attempts) > 1:
                st.code(a.sparql, language="sparql")
        if res.timings:
            st.markdown("**Timings:** " + ", ".join(f"{k.replace('_', ' ')} {v:.1f}s" for k, v in res.timings.items()))


def main() -> None:
    settings = get_settings()
    st.title("💊 Drug Discovery KGQA")
    st.caption(
        "Ask questions about drugs, indications, contraindications, adverse event signals, approvals, "
        "targets and pathways. A local LLM translates your question into SPARQL, runs it on the "
        "knowledge graph, and answers from the results only."
    )

    with st.sidebar:
        st.header("Settings")
        backend = st.selectbox(
            "Knowledge graph", ["auto", "graphdb", "local"],
            index=["auto", "graphdb", "local"].index(settings.kg_backend)
            if settings.kg_backend in {"auto", "graphdb", "local"} else 0,
            help="auto = GraphDB if it is running, otherwise the local Turtle files",
        )
        try:
            kg, linker, n_triples = load_kg(backend)
            st.success(f"{kg.describe()}\n\n{n_triples:,} triples, {len(linker)} named entities")
        except KGError as exc:
            st.error(str(exc))
            st.stop()

        llm = OllamaClient(settings)
        models = llm.available_models()
        if not models:
            st.error(
                f"Ollama is not reachable at {settings.ollama_url} or has no models.\n\n"
                f"Start Ollama and run `ollama pull {settings.ollama_model}`."
            )
            st.stop()
        default = models.index(settings.ollama_model) if settings.ollama_model in models else 0
        llm.model = st.selectbox("Local LLM (Ollama)", models, index=default)
        settings.max_attempts = st.slider("Max SPARQL attempts", 1, 5, settings.max_attempts)

        if st.button("Clear conversation"):
            st.session_state.history = []

        st.divider()
        st.caption("Try an example")
        for q in EXAMPLE_QUESTIONS:
            if st.button(q, width="stretch"):
                st.session_state.pending = q

    history: list[QAResult] = st.session_state.setdefault("history", [])
    for res in history:
        with st.chat_message("user"):
            st.markdown(res.question)
        with st.chat_message("assistant"):
            render_result(res)

    question = st.chat_input("Ask a question about the knowledge graph")
    question = question or st.session_state.pop("pending", None)
    if question:
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            with st.spinner(f"Thinking with {llm.model}..."):
                res = KGQA(kg, llm, settings, linker).ask(question)
            render_result(res)
        history.append(res)


main()
