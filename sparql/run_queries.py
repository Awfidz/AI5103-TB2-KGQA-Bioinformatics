"""Run every Step 3 SPARQL query and write the queries + results to .txt files.

Usage (from the repository root):
    .venv\\Scripts\\python sparql\\run_queries.py              # auto: GraphDB if reachable, else local .ttl
    .venv\\Scripts\\python sparql\\run_queries.py --backend local

Read queries (SELECT / CONSTRUCT / DESCRIBE) run against the selected backend.
Update queries (INSERT / DELETE) never touch the shared KG: they run on an
in-memory copy (snapshot) of it, with a verification query before and after,
so GraphDB repository is left unchanged.

Outputs:
    sparql/results/<query>.txt                 one file per query
    sparql/sparql_queries_and_results.txt      everything in one file (submission)
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "kgqa"))

from kgqa.config import get_settings  # noqa: E402
from kgqa.kg import BaseKG, LocalKG, format_table, get_kg, query_form  # noqa: E402

QUERY_DIR = HERE / "queries"
RESULT_DIR = HERE / "results"
COMBINED = HERE / "sparql_queries_and_results.txt"

PFX = """PREFIX :     <https://itb.ac.id/a5103/tubes_2#>
PREFIX res:  <https://itb.ac.id/a5103/tubes_2/resource/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
"""

# Queries that show the effect of each update (run before and after it).
VERIFY = {
    "u1_insert.rq": PFX
    + """SELECT ?drug ?drugName ?approval ?agencyName ?approvalDate
WHERE {
  ?drug rdfs:label ?drugName ;
        :hasApproval ?approval .
  FILTER (LCASE(STR(?drugName)) = "empagliflozin")
  ?approval :approvedBy/rdfs:label ?agencyName ;
            :approvalDate ?approvalDate .
}""",
    "u2_delete.rq": PFX
    + """SELECT ?signal ?drugName ?eventName ?llr
WHERE {
  ?signal a :AdverseSignal ;
          :llrScore ?llr ;
          :reportsEvent/rdfs:label ?eventName .
  ?drug :hasAdverseSignal ?signal ;
        rdfs:label ?drugName .
  FILTER (?llr < 100.0)
}
ORDER BY ?llr""",
}

RULE = "=" * 100
THIN = "-" * 100


def parse_header(text: str) -> tuple[str, str]:
    """Return (title, type) from the leading comment block.

    The block looks like:
        # CQ01: question text...
        #       continuation of the question
        # Type: SELECT
        # Note: ...
    """
    title_parts: list[str] = []
    kind = ""
    current = None
    for line in text.splitlines():
        if not line.startswith("#"):
            break
        body = line[1:]
        stripped = body.strip()
        key = stripped.split(":", 1)[0] if ":" in stripped else ""
        if key and " " not in key and body.startswith(" " + key):
            current = key.upper()
            value = stripped.split(":", 1)[1].strip()
            if current == "TYPE":
                kind = value
            elif current not in {"NOTE"} and not title_parts:
                title_parts.append(value)
                current = "TITLE"
        elif current == "TITLE":
            title_parts.append(stripped)
    return " ".join(title_parts), kind


_SCI_DOUBLE = re.compile(r"(?<![\w\".:-])(-?\d+(?:\.\d+)?[eE][+-]?\d+)(?![\w\"])")


def readable_doubles(ttl: str) -> str:
    """rdflib writes xsd:double as 1.4883e+02; show "148.83"^^xsd:double instead (same value and type)."""
    return _SCI_DOUBLE.sub(lambda m: f'"{float(m.group(1))!r}"^^xsd:double', ttl)


def run_read(kg: BaseKG, query: str) -> tuple[str, str]:
    form, result = kg.run(query)
    if form == "SELECT":
        rows = result.as_text_rows()
        return form, f"{format_table(result.variables, rows)}\n\n({len(rows)} row(s))"
    if form in {"CONSTRUCT", "DESCRIBE"}:
        ttl = readable_doubles(result.serialize(format="turtle").strip())
        return form, f"{ttl}\n\n({len(result)} triple(s))"
    if form == "ASK":
        return form, f"ASK result: {result}"
    raise ValueError(f"Not a read query: {form}")


def run_update(sandbox: LocalKG, name: str, query: str) -> str:
    verify = VERIFY.get(name)
    parts = []
    before_n = sandbox.triple_count()
    if verify:
        res = sandbox.select(verify)
        parts.append("Verification query:\n" + verify)
        parts.append("BEFORE the update:\n" + format_table(res.variables, res.as_text_rows())
                     + f"\n\n({len(res)} row(s))")
    sandbox.update(query)
    after_n = sandbox.triple_count()
    if verify:
        res = sandbox.select(verify)
        parts.append("AFTER the update:\n" + format_table(res.variables, res.as_text_rows())
                     + f"\n\n({len(res)} row(s))")
    diff = after_n - before_n
    parts.append(f"Triple count: {before_n} -> {after_n} ({'+' if diff >= 0 else ''}{diff})")
    return "\n\n".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--backend", choices=["auto", "graphdb", "local"], help="override KG_BACKEND")
    args = ap.parse_args()
    if args.backend:
        os.environ["KG_BACKEND"] = args.backend

    kg = get_kg(get_settings())
    print(f"Backend: {kg.describe()}  ({kg.triple_count()} triples)")
    sandbox: LocalKG | None = None

    RESULT_DIR.mkdir(exist_ok=True)
    sections = []
    files = sorted(QUERY_DIR.glob("*.rq"))
    for path in files:
        text = path.read_text(encoding="utf-8")
        title, kind = parse_header(text)
        form = query_form(text)
        try:
            if form == "UPDATE":
                if sandbox is None:
                    sandbox = LocalKG(graph=kg.snapshot())
                kind = kind or "UPDATE"
                body = run_update(sandbox, path.name, text)
                note = "(run on an in-memory copy of the KG; the shared KG is not modified)"
            else:
                kind, body = run_read(kg, text)
                note = ""
        except Exception as exc:  # keep going so one bad query does not hide the rest
            kind, body, note = form, f"ERROR: {exc}", ""
            print(f"  ! {path.name}: {exc}")

        section = "\n".join([
            RULE,
            f"{path.stem.upper()}  [{kind}]",
            title,
            RULE,
            "",
            "QUERY",
            THIN,
            text.strip(),
            "",
            ("RESULT " + note).strip(),
            THIN,
            body,
            "",
        ])
        (RESULT_DIR / f"{path.stem}.txt").write_text(section, encoding="utf-8")
        sections.append(section)
        print(f"  ok {path.name}")

    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    head = "\n".join([
        "AI5103 Foundational AI - KGQA Assignment, Step 3: SPARQL queries and results",
        "Ontology: Pharmacotherapy and Drug Discovery Ontology (https://itb.ac.id/a5103/tubes_2)",
        f"Backend:  {kg.describe()} - {kg.triple_count()} triples",
        f"Run at:   {stamp}",
        "",
        "Contents: CQ01-CQ15 (competency questions as SELECT/CONSTRUCT), "
        "U1 INSERT, U2 DELETE with FILTER, U3 DESCRIBE.",
        "",
    ])
    COMBINED.write_text(head + "\n" + "\n".join(sections), encoding="utf-8")
    print(f"Wrote {COMBINED.relative_to(HERE.parent)} and {len(files)} files in {RESULT_DIR.relative_to(HERE.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
