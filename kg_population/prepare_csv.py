"""Export deterministic CSV sources from the dataset and curated ID manifest."""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "dataset" / "json"
WORK_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = WORK_DIR / "data_csv"
CURATED_FILE = WORK_DIR / "curated_ids.json"


def load_json(path: Path) -> Any:
    if not path.is_file():
        raise FileNotFoundError(f"Required file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_table(name: str) -> list[dict[str, Any]]:
    rows = load_json(SOURCE_DIR / f"{name}.json")
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError(f"Expected a JSON array of records in {SOURCE_DIR / f'{name}.json'}")
    return rows


def index_table(name: str, key: str) -> dict[str, dict[str, Any]]:
    result = {}
    for row in load_table(name):
        value = row.get(key)
        if value is None:
            continue
        identifier = str(value)
        if identifier in result:
            raise ValueError(f"Duplicate {key}={identifier} in {name}.json")
        result[identifier] = row
    return result


def select(index: dict[str, dict[str, Any]], ids: list[str], table_name: str) -> list[dict[str, Any]]:
    missing = [identifier for identifier in ids if identifier not in index]
    if missing:
        raise ValueError(f"Curated IDs missing from {table_name}.json: {missing[:10]}")
    return [dict(index[identifier]) for identifier in ids]


def pair_set(rows: list[dict[str, Any]], left: str, right: str) -> set[tuple[str, str]]:
    return {
        (str(row[left]), str(row[right]))
        for row in rows
        if row.get(left) is not None and row.get(right) is not None
    }


def check_edges(actual: set[tuple[str, str]], expected: list[list[str]], name: str) -> None:
    expected_set = {tuple(pair) for pair in expected}
    if actual != expected_set:
        missing = sorted(expected_set - actual)
        extra = sorted(actual - expected_set)
        raise ValueError(f"{name} edge mismatch: {len(missing)} missing, {len(extra)} unexpected.")


def write_csv(name: str, rows: list[dict[str, Any]], columns: list[str]) -> None:
    with (OUTPUT_DIR / name).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def prepare() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    curated = load_json(CURATED_FILE)
    entities = curated["entities"]
    edges = curated["edges"]

    drugs = select(index_table("drug", "struct_id"), entities["drugs"], "drug")
    agencies = entities["agencies"]
    agency_labels = {agency["id"]: agency["label"] for agency in agencies}
    approvals = select(index_table("approval", "approval_id"), entities["approvals"], "approval")
    approval_agencies = {approval: agency for approval, agency in edges["approval_agency"]}
    for row in approvals:
        agency_id = approval_agencies.get(str(row["approval_id"]))
        if agency_id not in agency_labels or row.get("agency") != agency_labels[agency_id]:
            raise ValueError(f"Approval/agency data mismatch for {row['approval_id']}")
        row["agency_slug"] = agency_id

    diseases = select(index_table("disease", "concept_id"), entities["diseases"], "disease")
    associations_by_type = {
        "indication": select(
            index_table("association", "assoc_id"),
            entities["associations"]["indication"],
            "association",
        ),
        "contraindication": select(
            index_table("association", "assoc_id"),
            entities["associations"]["contraindication"],
            "association",
        ),
        "off_label_use": select(
            index_table("association", "assoc_id"),
            entities["associations"]["off_label_use"],
            "association",
        ),
    }
    associations = [
        row for group in associations_by_type.values() for row in group
    ]
    expected_relationships = {
        "indication": "indication",
        "contraindication": "contraindication",
        "off_label_use": "off-label use",
    }
    for relationship, rows in associations_by_type.items():
        for row in rows:
            if str(row.get("relationship_name", "")).strip().lower() != expected_relationships[relationship]:
                raise ValueError(f"Association type mismatch for {row['assoc_id']}")
    check_edges(
        pair_set(associations, "struct_id", "assoc_id"),
        edges["drug_association"],
        "drug-association",
    )
    check_edges(
        pair_set(associations, "assoc_id", "concept_id"),
        edges["association_disease"],
        "association-disease",
    )

    adverse_events = select(
        index_table("adverse_event", "meddra_code"),
        entities["adverse_events"],
        "adverse_event",
    )
    adverse_signals = select(
        index_table("adverse_signal", "signal_id"),
        entities["adverse_signals"],
        "adverse_signal",
    )
    check_edges(
        pair_set(adverse_signals, "struct_id", "signal_id"),
        edges["drug_adverse_signal"],
        "drug-adverse-signal",
    )
    check_edges(
        pair_set(adverse_signals, "signal_id", "meddra_code"),
        edges["signal_event"],
        "signal-event",
    )

    targets = select(index_table("target", "target_id"), entities["targets"], "target")
    proteins = select(index_table("protein", "accession"), entities["proteins"], "protein")
    pathways = select(index_table("pathway", "pathway_id"), entities["pathways"], "pathway")

    bioactivity = load_table("bioactivity")
    curated_target_edges = {tuple(pair) for pair in edges["drug_target"]}
    source_target_edges = pair_set(bioactivity, "struct_id", "target_id")
    if not curated_target_edges <= source_target_edges:
        raise ValueError("A curated drug-target edge is absent from bioactivity.json")
    drug_targets = [
        {"struct_id": drug_id, "target_id": target_id}
        for drug_id, target_id in edges["drug_target"]
    ]

    target_protein_source = load_table("target_protein")
    curated_target_protein_edges = {tuple(pair) for pair in edges["target_protein"]}
    if not curated_target_protein_edges <= pair_set(target_protein_source, "target_id", "accession"):
        raise ValueError("A curated target-protein edge is absent from target_protein.json")
    target_proteins = [
        {"target_id": target_id, "accession": accession}
        for target_id, accession in edges["target_protein"]
    ]

    protein_pathway_source = load_table("protein_pathway")
    curated_pathway_edges = {tuple(pair) for pair in edges["protein_pathway"]}
    source_pathway_edges = pair_set(protein_pathway_source, "accession", "pathway_id")
    if not curated_pathway_edges <= source_pathway_edges:
        raise ValueError("A curated protein-pathway edge is absent from protein_pathway.json")
    protein_pathways = [
        {"accession": accession, "pathway_id": pathway_id}
        for accession, pathway_id in edges["protein_pathway"]
    ]

    drug_approval_edges = pair_set(approvals, "struct_id", "approval_id")
    check_edges(drug_approval_edges, edges["drug_approval"], "drug-approval")

    exports = {
        "drug_small.csv": (
            [row for row in drugs if row.get("smiles")],
            ["struct_id", "name", "smiles", "cd_molweight"],
        ),
        "drug_nonsmall.csv": (
            [row for row in drugs if not row.get("smiles")],
            ["struct_id", "name", "cd_molweight"],
        ),
        "agency.csv": (
            [{"agency_slug": row["id"], "agency": row["label"]} for row in agencies],
            ["agency_slug", "agency"],
        ),
        "approval.csv": (
            approvals,
            ["approval_id", "struct_id", "agency_slug", "approval_date"],
        ),
        "disease.csv": (diseases, ["concept_id", "concept_name"]),
        "assoc_indication.csv": (
            associations_by_type["indication"],
            ["assoc_id", "concept_id"],
        ),
        "assoc_contraindication.csv": (
            associations_by_type["contraindication"],
            ["assoc_id", "concept_id"],
        ),
        "assoc_offlabel.csv": (
            associations_by_type["off_label_use"],
            ["assoc_id", "concept_id"],
        ),
        "association_clean.csv": (associations, ["assoc_id", "struct_id"]),
        "adverse_event.csv": (adverse_events, ["meddra_code", "meddra_name"]),
        "adverse_signal.csv": (
            adverse_signals,
            ["signal_id", "struct_id", "meddra_code", "llr"],
        ),
        "target_clean.csv": (targets, ["target_id", "target_name"]),
        "drug_target.csv": (drug_targets, ["struct_id", "target_id"]),
        "protein.csv": (proteins, ["accession", "protein_name"]),
        "target_protein.csv": (target_proteins, ["target_id", "accession"]),
        "pathway.csv": (pathways, ["pathway_id", "pathway_name"]),
        "protein_pathway.csv": (
            protein_pathways,
            ["accession", "pathway_id"],
        ),
    }
    for filename, (rows, columns) in exports.items():
        write_csv(filename, rows, columns)

    count = sum(
        len(value) if isinstance(value, list) else sum(len(group) for group in value.values())
        for value in entities.values()
    )
    if count != curated["expected_individuals"]:
        raise ValueError(
            f"Curated manifest count is {count}, expected {curated['expected_individuals']}."
        )
    print(f"Prepared {len(exports)} CSV files for {count} curated entities.")
    print(
        f"Edges -> targets={len(drug_targets)}, hasComponent={len(target_proteins)}, "
        f"participatesIn={len(protein_pathways)}"
    )
    return count


def main() -> int:
    # Keep relative paths stable regardless of the caller's working directory.
    os.chdir(Path(__file__).resolve().parent)
    prepare()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
