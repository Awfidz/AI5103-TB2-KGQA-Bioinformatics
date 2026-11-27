"""Load the Step 4 graph, materialize derived types, validate and export it."""

from __future__ import annotations

import os
import re
from pathlib import Path

import requests
from rdflib import Graph

ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY = ROOT / "ontology" / "drug_discovery.ttl"
ASSERTED_KG = ROOT / "kg" / "drug_discovery_kg.ttl"
MATERIALIZE_FILE = Path(__file__).resolve().parent / "graphdb_materialize.sparql"
EXPORT = Path(__file__).resolve().parent / "graphdb_export" / "drug_discovery_graphdb_final.ttl"
BASE_URL = os.getenv("GRAPHDB_URL", "http://localhost:7200").rstrip("/")
REPOSITORY = os.getenv("GRAPHDB_REPO", "drug-kgqa")
ENDPOINT = f"{BASE_URL}/repositories/{REPOSITORY}"
TIMEOUT = float(os.getenv("GRAPHDB_TIMEOUT", "120"))
PREFIXES = """PREFIX : <https://itb.ac.id/a5103/tubes_2#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
"""


def select(query: str) -> list[dict]:
    try:
        response = requests.post(
            ENDPOINT,
            data={"query": query},
            headers={"Accept": "application/sparql-results+json"},
            timeout=TIMEOUT,
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"Cannot query GraphDB at {ENDPOINT}: {exc}") from exc
    if not response.ok:
        raise RuntimeError(f"GraphDB query failed ({response.status_code}): {response.text[:500]}")
    return response.json()["results"]["bindings"]


def update(query: str) -> None:
    try:
        response = requests.post(
            f"{ENDPOINT}/statements",
            data={"update": query},
            timeout=TIMEOUT,
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"Cannot update GraphDB at {ENDPOINT}: {exc}") from exc
    if not response.ok:
        raise RuntimeError(f"GraphDB update failed ({response.status_code}): {response.text[:500]}")


def split_updates(text: str) -> list[str]:
    prefixes = "".join(line + "\n" for line in text.splitlines() if line.startswith("PREFIX"))
    body = "\n".join(line for line in text.splitlines() if not line.startswith("PREFIX"))
    updates = [part.strip() for part in re.split(r"^\s*;\s*$", body, flags=re.M)]
    updates = [prefixes + part for part in updates if "INSERT" in part]
    if len(updates) != 4:
        raise ValueError(f"Expected 4 INSERT updates, found {len(updates)}.")
    return updates


def count(query_body: str, variable: str = "?s") -> int:
    query = PREFIXES + f"\nSELECT (COUNT(DISTINCT {variable}) AS ?count) WHERE {{ {query_body} }}"
    rows = select(query)
    if len(rows) != 1 or "count" not in rows[0]:
        raise RuntimeError(f"Unexpected count response for: {query_body}")
    return int(rows[0]["count"]["value"])


def count_rows(query_body: str) -> int:
    query = PREFIXES + f"\nSELECT (COUNT(*) AS ?count) WHERE {{ {query_body} }}"
    rows = select(query)
    if len(rows) != 1 or "count" not in rows[0]:
        raise RuntimeError(f"Unexpected edge-count response for: {query_body}")
    return int(rows[0]["count"]["value"])


def verify() -> None:
    expected = {
        "Drug": ("?s a :Drug .", 10),
        "RegulatoryAgency": ("?s a :RegulatoryAgency .", 3),
        "RegulatoryApproval": ("?s a :RegulatoryApproval .", 16),
        "Disease": ("?s a :Disease .", 70),
        "Indication": ("?s a :Indication .", 29),
        "Contraindication": ("?s a :Contraindication .", 38),
        "OffLabelUse": ("?s a :OffLabelUse .", 16),
        "AdverseEvent": ("?s a :AdverseEvent .", 31),
        "AdverseSignal": ("?s a :AdverseSignal .", 32),
        "Target": ("?s a :Target .", 14),
        "Protein": ("?s a :Protein .", 22),
        "Pathway": ("?s a :Pathway .", 28),
        "SmallMoleculeDrug": ("?s a :SmallMoleculeDrug .", 9),
        "ApprovedDrug": ("?s a :ApprovedDrug .", 10),
        "HighRiskApprovedDrug": ("?s a :HighRiskApprovedDrug .", 9),
        "RepurposedApprovedDrug": ("?s a :RepurposedApprovedDrug .", 7),
        "StrongAdverseSignal": ("?s a :StrongAdverseSignal .", 30),
        "ProteinComplexTarget": ("?s a :ProteinComplexTarget .", 5),
    }
    for name, (body, expected_count) in expected.items():
        actual = count(body)
        if actual != expected_count:
            raise RuntimeError(f"{name}: expected {expected_count}, got {actual}")
        print(f"  {name}: {actual}")

    weak_signals = count("?s a :AdverseSignal ; :llrScore ?score . FILTER(xsd:double(?score) < 100.0)")
    if weak_signals != 2:
        raise RuntimeError(f"Expected 2 weak adverse signals, got {weak_signals}")
    target_edges = count_rows("?s :targets ?target .")
    component_edges = count_rows("?s :hasComponent ?protein .")
    pathway_edges = count_rows("?s :participatesIn ?pathway .")
    if (target_edges, component_edges, pathway_edges) != (14, 25, 45):
        raise RuntimeError(
            "Key edge counts differ: "
            f"targets={target_edges}, hasComponent={component_edges}, participatesIn={pathway_edges}"
        )

    repurposed = {
        row["label"]["value"]
        for row in select(PREFIXES + """
            SELECT DISTINCT ?label WHERE {
              ?drug a :RepurposedApprovedDrug ; rdfs:label ?label .
            }
        """)
    }
    expected_repurposed = {
        "atorvastatin", "chloroquine", "ciprofloxacin", "diazepam",
        "losartan", "metformin", "omeprazole",
    }
    if repurposed != expected_repurposed:
        raise RuntimeError(f"Unexpected repurposed drug set: {sorted(repurposed)}")

    complex_targets = {
        row["target"]["value"].rsplit("target_", 1)[-1]
        for row in select(PREFIXES + """
            SELECT ?target WHERE { ?target a :ProteinComplexTarget . }
        """)
    }
    if complex_targets != {"2731", "2732", "2733", "2752", "2815"}:
        raise RuntimeError(f"Unexpected protein-complex targets: {sorted(complex_targets)}")

    pathway_count = count(
        "VALUES ?s { <https://itb.ac.id/a5103/tubes_2/resource/drug_1423> } "
        "?s :affectsPathway ?pathway .",
        variable="?pathway",
    )
    if pathway_count != 8:
        raise RuntimeError(f"Imatinib: expected 8 affected pathways, got {pathway_count}")


def upload(path: Path) -> None:
    try:
        response = requests.post(
            f"{ENDPOINT}/statements",
            data=path.read_bytes(),
            headers={"Content-Type": "text/turtle"},
            timeout=TIMEOUT,
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"Cannot upload {path} to GraphDB: {exc}") from exc
    if not response.ok:
        raise RuntimeError(f"GraphDB upload failed for {path.name} ({response.status_code}): {response.text[:500]}")


def main() -> int:
    for path in (ONTOLOGY, ASSERTED_KG):
        if not path.is_file():
            raise FileNotFoundError(f"Run the TBox exporter and RML materializer first: {path}")

    try:
        response = requests.get(f"{ENDPOINT}/size", timeout=5)
    except requests.RequestException as exc:
        raise RuntimeError(
            f"GraphDB repository {REPOSITORY!r} is unreachable at {BASE_URL}; "
            "create an empty repository with the OWL2-RL ruleset first."
        ) from exc
    if not response.ok:
        raise RuntimeError(
            f"GraphDB repository {REPOSITORY!r} is unavailable ({response.status_code}); "
            "create it with the OWL2-RL ruleset first."
        )
    size = int(response.text.strip())
    if size != 0:
        raise RuntimeError(
            f"Repository {REPOSITORY!r} is not empty ({size} triples). "
            "Use a fresh OWL2-RL repository to avoid stale data."
        )

    upload(ONTOLOGY)
    upload(ASSERTED_KG)
    for statement in split_updates(MATERIALIZE_FILE.read_text(encoding="utf-8")):
        update(statement)
    print(f"Applied {MATERIALIZE_FILE.name}")
    verify()

    EXPORT.parent.mkdir(parents=True, exist_ok=True)
    try:
        response = requests.get(
            f"{ENDPOINT}/statements",
            params={"infer": "false"},
            headers={"Accept": "text/turtle"},
            timeout=TIMEOUT,
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"Cannot export the final GraphDB graph: {exc}") from exc
    if not response.ok:
        raise RuntimeError(f"GraphDB export failed ({response.status_code}): {response.text[:500]}")
    exported = Graph().parse(data=response.text, format="turtle")
    if not exported:
        raise RuntimeError("GraphDB returned an empty final export.")
    EXPORT.write_text(response.text, encoding="utf-8")
    print(f"Exported {len(exported):,} triples to {EXPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
