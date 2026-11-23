"""Evaluate the KGQA app against competency questions, plus extra questions.

Each competency question is read from the header of its gold query in
sparql/queries/ (the official Indonesian text, or the English line with
--lang en) and asked to the app. List questions are scored by comparing the
app's result rows with the gold query's rows (recall of the expected values).
Yes/no questions (CQ03-CQ05) are scored on whether the written answer says
yes or no. Extra questions without gold queries (typos, synonyms, Indonesian,
out-of-scope) are listed for manual review.

Usage (Ollama must be running):
    .venv\\Scripts\\python kgqa\\evaluate.py                    # Indonesian CQ text, default model
    .venv\\Scripts\\python kgqa\\evaluate.py --lang en          # English CQ text
    .venv\\Scripts\\python kgqa\\evaluate.py --model qwen2.5:3b --only CQ03,CQ09

Writes kgqa/evaluation/eval_<model>_<lang>.md
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
import time
from pathlib import Path

from rdflib import RDFS, Graph

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from kgqa.config import get_settings  # noqa: E402
from kgqa.kg import BaseKG, compact, format_table, get_kg  # noqa: E402
from kgqa.linker import EntityLinker  # noqa: E402
from kgqa.llm import OllamaClient  # noqa: E402
from kgqa.pipeline import KGQA, NO_RESULTS_ANSWERS, QAResult  # noqa: E402
from kgqa.prompts import is_indonesian  # noqa: E402

QUERY_DIR = HERE.parent / "sparql" / "queries"
OUT_DIR = HERE / "evaluation"

# (id, gold query file, what to compare): a SELECT column name, "answer" for yes/no
# questions, or IRI fragments ("a|b") whose rdfs:labels are the expected values of a CONSTRUCT.
CQ_TESTS = [
    ("CQ01", "cq01_sildenafil_approvals.rq", "agencyName"),
    ("CQ02", "cq02_complex_targets.rq", "targetName"),
    ("CQ03", "cq03_diazepam_check.rq", "answer"),
    ("CQ04", "cq04_ciprofloxacin_check.rq", "answer"),
    ("CQ05", "cq05_trastuzumab_check.rq", "answer"),
    ("CQ06", "cq06_diabetes_infection.rq", "drugName"),
    ("CQ07", "cq07_hypercholesterolemia_myalgia.rq", "drugName"),
    ("CQ08", "cq08_offlabel_heart_failure.rq", "drugName"),
    ("CQ09", "cq09_imatinib_pathways.rq", "pathway_"),
    ("CQ10", "cq10_chloroquine_safety_profile.rq", "ae_|disease_"),
    ("CQ11", "cq11_hepatic_failure_contraindications.rq", "drugName"),
    ("CQ12", "cq12_diazepam_top_signals.rq", "eventName"),
    ("CQ13", "cq13_fda_before_1990.rq", "drugName"),
    ("CQ14", "cq14_small_molecules_lipinski.rq", "drugName"),
    ("CQ15", "cq15_high_risk_drugs.rq", "drugName"),
]

EXTRA_TESTS = [
    ("X1 typo", "What is metfromin indicated for?"),
    ("X2 synonym", "Which drugs treat high cholesterol?"),
    ("X3 Indonesian", "Apa saja kontraindikasi dari omeprazole?"),
    ("X4 aggregation", "Which drug has the most contraindications?"),
    ("X5 multi-hop", "Which drugs act on proteins that participate in GABA receptor activation?"),
    ("X6 out of scope", "What is the recommended daily dose of metformin?"),
]

_YES = re.compile(r"(?i)\b(ya|iya|yes|true|benar|betul)\b")
_NO = re.compile(r"(?i)\b(tidak|bukan|no|not|false)\b")


def question_text(file: str, lang: str) -> str:
    """The CQ text from the query header: the 'CQnn:' block (Indonesian) or the 'EN:' block."""
    blocks: dict[str, list[str]] = {}
    current = None
    for line in (QUERY_DIR / file).read_text(encoding="utf-8").splitlines():
        if not line.startswith("#"):
            break
        m = re.match(r"#\s(\w+):\s*(.*)", line)
        if m:
            current = m.group(1).upper()
            blocks[current] = [m.group(2).strip()]
        elif current:
            blocks[current].append(line.lstrip("#").strip())
    key = "EN" if lang == "en" else next(k for k in blocks if k.startswith("CQ"))
    return " ".join(blocks[key])


def _norm(value: str) -> str:
    value = value.strip().lower()
    try:
        return f"{float(value):.2f}"
    except ValueError:
        return re.sub(r"\s+", " ", value)


def gold_values(kg: BaseKG, file: str, key: str) -> set[str]:
    query = (QUERY_DIR / file).read_text(encoding="utf-8")
    form, result = kg.run(query)
    if form == "SELECT":
        return {_norm(compact(r[key])) for r in result.rows if key in r}
    assert isinstance(result, Graph)
    fragments = key.split("|")
    return {_norm(str(o)) for s, o in result.subject_objects(RDFS.label) if any(f in str(s) for f in fragments)}


def produced_values(res: QAResult) -> set[str]:
    if res.result is None:
        return set()
    values = set()
    for row in res.result.as_text_rows():
        for v in row.values():
            values.update(_norm(part) for part in v.split(", "))
            values.add(_norm(v))
    return values


def answer_polarity(res: QAResult) -> str | None:
    """'true' / 'false' from the first yes/no word of the written answer, else None."""
    text = res.answer or ""
    if not text or text in NO_RESULTS_ANSWERS:
        return None
    yes, no = _YES.search(text), _NO.search(text)
    if yes and (not no or yes.start() < no.start()):
        return "true"
    if no:
        return "false"
    return None


def answer_mentions(res: QAResult, gold: set[str]) -> float | None:
    """Share of the expected names that the written answer mentions (numbers are ignored)."""
    names = {g for g in gold if not re.fullmatch(r"-?\d+(\.\d+)?", g)}
    if not names:
        return None
    text = re.sub(r"\s+", " ", (res.answer or "").lower())
    return sum(1 for g in names if g in text) / len(names)


def language_ok(question: str, res: QAResult) -> bool:
    return bool(res.answer) and is_indonesian(question) == is_indonesian(res.answer)


def md_escape(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", help="Ollama model (default: OLLAMA_MODEL or qwen2.5:7b)")
    ap.add_argument("--lang", choices=["id", "en"], default="id", help="ask the CQs in Indonesian or English")
    ap.add_argument("--only", help="comma-separated test ids, e.g. CQ01,X3")
    args = ap.parse_args()

    settings = get_settings()
    kg = get_kg(settings)
    llm = OllamaClient(settings, model=args.model)
    if not llm.is_up():
        print(f"Ollama is not reachable at {settings.ollama_url}")
        return 1
    qa = KGQA(kg, llm, settings, EntityLinker(kg))
    only = set(args.only.split(",")) if args.only else None

    print(f"KG: {kg.describe()} | model: {llm.model} | CQ language: {args.lang}")
    summary, details = [], []
    n_correct = n_verbose = n_partial = 0
    n_answer_ok = n_lang_ok = 0
    total_time = 0.0

    for tid, file, key in CQ_TESTS:
        if only and tid not in only:
            continue
        question = question_text(file, args.lang)
        gold = gold_values(kg, file, key)
        t = time.perf_counter()
        res = qa.ask(question)
        elapsed = time.perf_counter() - t
        total_time += elapsed
        rows = len(res.result) if res.result is not None else 0
        if key == "answer":
            expected = next(iter(gold))
            said = answer_polarity(res)
            verdict = "correct" if said == expected else "wrong"
            score = f"said {said or 'unclear'}"
            note = f"{verdict}: expected {expected}, answer says {said or 'unclear'}"
            mention = 1.0 if said == expected else 0.0
        else:
            got = produced_values(res)
            recall = len(gold & got) / len(gold) if gold else 0.0
            if recall == 1.0:
                verdict = "correct" if rows <= max(2 * len(gold), len(gold) + 5) else "verbose"
            else:
                verdict = "partial" if recall > 0 else "wrong"
            score = f"recall {recall:.2f}"
            note = f"{verdict}, recall {recall:.2f} (expected: {', '.join(sorted(gold))})"
            mention = answer_mentions(res, gold)
        n_correct += verdict == "correct"
        n_verbose += verdict == "verbose"
        n_partial += verdict == "partial"
        lang = language_ok(question, res)
        n_lang_ok += lang
        n_answer_ok += mention is not None and mention == 1.0
        mention_txt = "-" if mention is None else f"{mention:.2f}"
        print(f"  {tid}: {verdict:8s} {score} rows={rows} answer={mention_txt} lang={'ok' if lang else 'WRONG'} "
              f"attempts={len(res.attempts)} {elapsed:.1f}s")
        summary.append(f"| {tid} | {md_escape(question)} | {verdict} | {score} | {mention_txt} | "
                       f"{'ok' if lang else 'wrong'} | {rows} | {len(gold)} | {len(res.attempts)} | {elapsed:.1f} |")
        details.append((tid, question, res, note))

    extra_rows = []
    for tid, question in EXTRA_TESTS:
        if only and tid.split()[0] not in only:
            continue
        t = time.perf_counter()
        res = qa.ask(question)
        elapsed = time.perf_counter() - t
        total_time += elapsed
        rows = len(res.result) if res.result is not None else 0
        print(f"  {tid}: rows={rows} attempts={len(res.attempts)} {elapsed:.1f}s")
        extra_rows.append(f"| {tid} | {md_escape(question)} | {md_escape(res.answer or res.error or '')} | "
                          f"{rows} | {len(res.attempts)} | {elapsed:.1f} |")
        details.append((tid, question, res, "manual review"))

    n_cq = len(summary)
    OUT_DIR.mkdir(exist_ok=True)
    safe_model = re.sub(r"[^\w.-]", "_", llm.model)
    out = OUT_DIR / f"eval_{safe_model}_{args.lang}.md"
    lines = [
        f"# KGQA evaluation - {llm.model}",
        "",
        f"- Run at: {dt.datetime.now():%Y-%m-%d %H:%M}",
        f"- Knowledge graph: {kg.describe()} ({kg.triple_count()} triples)",
        f"- Model: `{llm.model}` via Ollama, context {settings.ollama_num_ctx} tokens, "
        f"max {settings.max_attempts} SPARQL attempts",
        f"- Competency questions: **{n_correct}/{n_cq} correct**, {n_verbose} verbose, {n_partial} partial, "
        f"{n_cq - n_correct - n_verbose - n_partial} wrong",
        f"- Written answers: **{n_answer_ok}/{n_cq}** state every expected item (or the right Yes/No); "
        f"{n_lang_ok}/{n_cq} in the question's language",
        f"- Total time: {total_time:.0f}s",
        "",
        "List questions: recall = share of the gold query's expected values found in the app's result rows.",
        "Yes/no questions (CQ03-CQ05): scored on whether the written answer says yes or no.",
        "Answer mentions: share of the expected names that appear in the written answer (1.00 = all).",
        "Verdict: *correct* = recall 1 and at most ~2x the expected rows; *verbose* = recall 1 but many more rows",
        "(e.g. duplicated combinations); *partial* = some expected values missing; *wrong* = none found.",
        "Written answers are not scored automatically - see the details section.",
        "",
        f"## Competency questions (asked in {'English' if args.lang == 'en' else 'Indonesian'})",
        "",
        "| ID | Question | Verdict | Score | Answer mentions | Language | Rows | Expected values | Attempts | Time (s) |",
        "|---|---|---|---|---|---|---|---|---|---|",
        *summary,
        "",
        "## Extra questions (manual review)",
        "",
        "| ID | Question | Answer | Rows | Attempts | Time (s) |",
        "|---|---|---|---|---|---|",
        *extra_rows,
        "",
        "## Details",
        "",
    ]
    for tid, question, res, verdict in details:
        lines += [f"### {tid}: {question}", "", f"*{verdict}*", ""]
        if res.entities:
            lines.append("Linked entities: " + ", ".join(f"`{m.entity.label}`" for m in res.entities))
            lines.append("")
        for i, a in enumerate(res.attempts, 1):
            status = f"error: {a.error}" if a.error else f"{a.rows} row(s)"
            lines += [f"Attempt {i} ({md_escape(status)}):", "", "```sparql", a.sparql.strip(), "```", ""]
        if res.result is not None and len(res.result):
            lines += ["```", format_table(res.result.variables, res.result.as_text_rows()[:15]), "```", ""]
        lines += [f"**Answer:** {res.answer or res.error}", ""]
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n{n_correct}/{n_cq} correct, {n_verbose} verbose, {n_partial} partial. "
          f"Report: {out.relative_to(HERE.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
