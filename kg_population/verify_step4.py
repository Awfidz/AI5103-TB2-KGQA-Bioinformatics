"""Verify Step 4 outputs: CSV vs dataset.xlsx, materialized ABox, local inference."""

from __future__ import annotations

import csv
import math
import os
import re
import sys
from pathlib import Path

import pandas as pd
from rdflib import Graph, Literal, Namespace, RDF, URIRef
from rdflib.namespace import OWL

WORK_DIR = Path(__file__).resolve().parent
ROOT = WORK_DIR.parent
TBOX = ROOT / "ontology" / "drug_discovery.ttl"
ONTO = Namespace("https://itb.ac.id/a5103/tubes_2#")
RES = "https://itb.ac.id/a5103/tubes_2/resource/"
failures: list[str] = []


def check(ok: bool, message: str) -> None:
    print(("PASS " if ok else "FAIL ") + message)
    if not ok:
        failures.append(message)


def norm(value) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    text = str(value).strip()
    try:
        number = float(text)
        return repr(number)
    except ValueError:
        return text


# ---------------------------------------------------------------- 1. CSV vs xlsx
SHEET_FOR_CSV = {
    "drug_small.csv": "drug", "drug_nonsmall.csv": "drug", "approval.csv": "approval",
    "disease.csv": "disease", "assoc_indication.csv": "association",
    "assoc_contraindication.csv": "association", "assoc_offlabel.csv": "association",
    "association_clean.csv": "association", "adverse_event.csv": "adverse_event",
    "adverse_signal.csv": "adverse_signal", "target_clean.csv": "target",
    "drug_target.csv": "bioactivity", "protein.csv": "protein",
    "target_protein.csv": "target_protein", "pathway.csv": "pathway",
    "protein_pathway.csv": "protein_pathway",
}
CSV_COLUMN_ALIAS = {  # CSV column -> sheet column
    ("disease.csv", "concept_name"): "concept_name",
}


def verify_csv_against_xlsx() -> None:
    sheets = pd.read_excel(ROOT / "dataset" / "dataset.xlsx", sheet_name=None, dtype=object)
    total = 0
    for name, sheet_name in SHEET_FOR_CSV.items():
        with (WORK_DIR / "data_csv" / name).open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        total_rows = len(rows)
        sheet = sheets[sheet_name]
        columns = [c for c in rows[0].keys() if c in sheet.columns]
        if name == "approval.csv":
            sheet = sheet.assign(agency_slug=sheet["agency"].astype(str).str.lower())
            columns = [c for c in rows[0].keys() if c in sheet.columns]
        source = {tuple(norm(v) for v in rec) for rec in sheet[columns].itertuples(index=False)}
        missing = [r for r in rows if tuple(norm(r[c]) for c in columns) not in source]
        check(not missing, f"{name}: {total_rows} rows match {sheet_name} sheet on {columns}")
        if name in ("drug_small.csv", "drug_nonsmall.csv"):
            pass
    # specific traps
    bio = sheets["bioactivity"]
    pair = bio[(bio.struct_id.astype(str) == "607") & (bio.target_id.astype(str) == "5515")]
    check(len(pair) >= 1 and pair["moa"].isna().all(), "(607, 5515) exists in xlsx with moa=NaN")
    with (WORK_DIR / "data_csv" / "drug_target.csv").open(encoding="utf-8") as stream:
        edges = {(r["struct_id"], r["target_id"]) for r in csv.DictReader(stream)}
    check(("607", "5515") in edges and len(edges) == 14, "drug_target.csv has 14 edges incl. (607, 5515)")
    with (WORK_DIR / "data_csv" / "protein_pathway.csv").open(encoding="utf-8") as stream:
        pp = {(r["accession"], r["pathway_id"]) for r in csv.DictReader(stream)}
    check(len(pp) == 45 and ("P04626", "R-HSA-1257604") not in pp, "protein_pathway.csv has exactly 45 edges, no P04626/R-HSA-1257604")
    entity_files = ["drug_small.csv", "drug_nonsmall.csv", "agency.csv", "approval.csv", "disease.csv",
                    "association_clean.csv", "adverse_event.csv", "adverse_signal.csv",
                    "target_clean.csv", "protein.csv", "pathway.csv"]
    for name in entity_files:
        with (WORK_DIR / "data_csv" / name).open(encoding="utf-8") as stream:
            total += sum(1 for _ in csv.DictReader(stream))
    check(total == 309, f"entity rows across CSVs = {total} (expected 309)")
    check(len(list((WORK_DIR / "data_csv").glob("*.csv"))) == 17, "data_csv has 17 files")


# ------------------------------------------------------- 2. Materialized ABox
def lit_key(o):
    if isinstance(o, Literal):
        return ("L", str(o), str(o.datatype) if o.datatype else None, o.language)
    return ("U", str(o))


def abox_triples(graph: Graph) -> set:
    return {
        (str(s), str(p), lit_key(o))
        for s, p, o in graph
        if isinstance(s, URIRef) and str(s).startswith(RES)
    }


def verify_abox() -> Graph:
    """Validate the generated ABox against the curated manifest, not a duplicate ABox."""
    from kg_population.run_rml import validate

    generated = Graph().parse(ROOT / "kg" / "drug_discovery_kg.ttl", format="turtle")
    try:
        counts = validate(generated)
        check(True, f"materialized ABox matches curated manifest: {counts['RelevantEntities']} entities, {len(generated)} triples")
    except Exception as exc:
        check(False, f"materialized ABox validation failed: {exc}")
    return generated


# ---------------------------------------------------------- 3. TBox structure
def verify_tbox() -> None:
    tbox = Graph().parse(TBOX, format="turtle")
    text = TBOX.read_text(encoding="utf-8")
    classes = {s for s in tbox.subjects(RDF.type, OWL.Class) if isinstance(s, URIRef)}
    objprops = set(tbox.subjects(RDF.type, OWL.ObjectProperty))
    dataprops = set(tbox.subjects(RDF.type, OWL.DatatypeProperty))
    disjoint = set(tbox.subjects(RDF.type, OWL.AllDisjointClasses))
    check(len(classes) == 20, f"TBox named classes = {len(classes)} (expected 20)")
    check(len(objprops) == 10, f"TBox object properties = {len(objprops)} (expected 10)")
    check(len(dataprops) == 5, f"TBox datatype properties = {len(dataprops)} (expected 5)")
    check(len(disjoint) == 3, f"TBox AllDisjointClasses blocks = {len(disjoint)} (expected 3)")
    check("ABOX" not in text and "@prefix res:" not in text, "TBox has no ABOX section and no res: prefix")
    check(not any(str(s).startswith(RES) for s in tbox.subjects()), "TBox has no resource individuals")


# --------------------------------------------------------- 4. Local inference
def verify_inference(generated: Graph) -> None:
    import owlrl
    from rdflib.plugins.sparql import prepareQuery  # noqa: F401

    from kg_population.materialize_graphdb import split_updates

    graph = Graph()
    graph.parse(TBOX, format="turtle")
    # owlrl, unlike GraphDB, turns (inverse-)functional axioms into owl:sameAs merges
    # and max-cardinality restrictions and owl:hasKey into owl:sameAs merges across unrelated
    # individuals, which pollutes counts. Drop these axioms for the
    # simulation only; the real TBox file is untouched.
    for marker in (OWL.FunctionalProperty, OWL.InverseFunctionalProperty):
        for prop in list(graph.subjects(RDF.type, marker)):
            graph.remove((prop, RDF.type, marker))
    for predicate in (OWL.maxCardinality, OWL.maxQualifiedCardinality, OWL.cardinality, OWL.qualifiedCardinality, OWL.hasKey):
        for triple in list(graph.triples((None, predicate, None))):
            graph.remove(triple)
    for triple in generated:
        graph.add(triple)

    def reason() -> None:
        owlrl.DeductiveClosure(
            owlrl.OWLRL_Semantics, rdfs_closure=False, axiomatic_triples=False, datatype_axioms=False
        ).expand(graph)

    reason()
    for statement in split_updates((WORK_DIR / "graphdb_materialize.sparql").read_text(encoding="utf-8")):
        graph.update(statement)
        reason()
    expected = {
        "ApprovedDrug": 10, "HighRiskApprovedDrug": 9, "ImatinibAffectsPathway": 8,
        "ProteinComplexTarget": 5, "RepurposedApprovedDrug": 7, "SmallMoleculeDrug": 9,
        "StrongAdverseSignal": 30,
    }
    query = (WORK_DIR / "graphdb_sanity_check.sparql").read_text(encoding="utf-8")
    actual = {str(row.check): int(row["count"]) for row in graph.query(query)}
    check(actual == expected, f"local OWL-RL + 4 INSERT sanity check: {actual}")


def main() -> int:
    os.chdir(WORK_DIR)
    sys.path.insert(0, str(ROOT))
    verify_csv_against_xlsx()
    generated = verify_abox()
    verify_tbox()
    verify_inference(generated)
    print(f"\n{len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
