"""Materialize the RML mappings and validate the resulting Turtle graph."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
from pathlib import Path

import morph_kgc
from rdflib import Graph, Literal, Namespace, OWL, RDF, RDFS
from rdflib.namespace import XSD

ROOT = Path(__file__).resolve().parents[1]
WORK_DIR = Path(__file__).resolve().parent
KG_DIR = ROOT / "kg"
OUTPUT = KG_DIR / "drug_discovery_kg.ttl"
CURATED_FILE = WORK_DIR / "curated_ids.json"
ONTO = Namespace("https://itb.ac.id/a5103/tubes_2#")
RES = Namespace("https://itb.ac.id/a5103/tubes_2/resource/")


def restore_llr_lexical_forms(graph: Graph) -> None:
    source = WORK_DIR / "data_csv" / "adverse_signal.csv"
    with source.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            subject = RES[f"signal_{row['signal_id']}"]
            values = list(graph.objects(subject, ONTO.llrScore))
            if len(values) != 1:
                raise ValueError(f"Expected one LLR value for {subject}, found {len(values)}.")
            graph.remove((subject, ONTO.llrScore, values[0]))
            graph.add((
                subject,
                ONTO.llrScore,
                Literal(row["llr"], datatype=XSD.double, normalize=False),
            ))


PREFIX_HEADER = (
    f"@prefix : <{ONTO}> .\n"
    f"@prefix res: <{RES}> .\n"
    f"@prefix owl: <{OWL}> .\n"
    f"@prefix rdfs: <{RDFS}> .\n"
    f"@prefix xsd: <{XSD}> .\n\n"
)


def prefixed_turtle(graph: Graph) -> str:
    """Serialize as prefixed Turtle while keeping xsd:double lexical forms verbatim.

    rdflib's Turtle writer rewrites doubles (e.g. 5981.245 -> 5.981245e+03), so the
    N-Triples lines are shortened with the prefixes instead.
    """
    ntriples = graph.serialize(format="nt")
    if isinstance(ntriples, bytes):
        ntriples = ntriples.decode("utf-8")
    iri = re.compile(r"<([^<>\s]+)>")
    shorteners = (
        (str(RES), "res:", re.compile(r"[A-Za-z0-9_]([A-Za-z0-9_-]*[A-Za-z0-9_])?")),
        (str(ONTO), ":", re.compile(r"[A-Za-z0-9_]+")),
        (str(OWL), "owl:", re.compile(r"[A-Za-z]+")),
        (str(RDFS), "rdfs:", re.compile(r"[A-Za-z]+")),
        (str(XSD), "xsd:", re.compile(r"[A-Za-z]+")),
    )

    def shorten(match: re.Match) -> str:
        value = match.group(1)
        if value == str(RDF.type):
            return "a"
        for namespace, prefix, local in shorteners:
            if value.startswith(namespace) and local.fullmatch(value[len(namespace):]):
                return prefix + value[len(namespace):]
        return match.group(0)

    lines = sorted(line for line in ntriples.splitlines() if line.strip())
    return PREFIX_HEADER + "\n".join(iri.sub(shorten, line) for line in lines) + "\n"


def resource_pairs(graph: Graph, predicate, left_prefix: str, right_prefix: str) -> set[tuple[str, str]]:
    result = set()
    for subject, _, object_ in graph.triples((None, predicate, None)):
        left, right = str(subject), str(object_)
        if not left.startswith(str(RES)) or not right.startswith(str(RES)):
            raise ValueError(f"Unexpected resource IRI for {predicate}: {subject}, {object_}")
        left, right = left[len(str(RES)):], right[len(str(RES)):]
        if not left.startswith(left_prefix) or not right.startswith(right_prefix):
            raise ValueError(f"Unexpected resource pair for {predicate}: {subject}, {object_}")
        result.add((left.removeprefix(left_prefix), right.removeprefix(right_prefix)))
    return result


def validate(graph: Graph) -> dict[str, int]:
    curated = json.loads(CURATED_FILE.read_text(encoding="utf-8"))
    entities = curated["entities"]
    association_types = (ONTO.Indication, ONTO.Contraindication, ONTO.OffLabelUse)
    classes = {
        "Drug": ONTO.Drug,
        "RegulatoryAgency": ONTO.RegulatoryAgency,
        "RegulatoryApproval": ONTO.RegulatoryApproval,
        "Disease": ONTO.Disease,
        "Indication": ONTO.Indication,
        "Contraindication": ONTO.Contraindication,
        "OffLabelUse": ONTO.OffLabelUse,
        "AdverseSignal": ONTO.AdverseSignal,
        "AdverseEvent": ONTO.AdverseEvent,
        "Target": ONTO.Target,
        "Protein": ONTO.Protein,
        "Pathway": ONTO.Pathway,
    }
    counts = {
        label: len(set(graph.subjects(RDF.type, class_)))
        for label, class_ in classes.items()
    }
    entity_sets = [set(graph.subjects(RDF.type, class_)) for class_ in classes.values()]
    total = len(set().union(*entity_sets))
    counts["RelevantEntities"] = total
    if total != 309:
        raise ValueError(f"Expected the curated 309 entities, materialized {total}.")
    named_individual_count = len(set(graph.subjects(RDF.type, OWL.NamedIndividual)))
    if named_individual_count != curated["expected_individuals"]:
        raise ValueError(
            f"Expected {curated['expected_individuals']} named individuals, "
            f"found {named_individual_count}."
        )
    expected_counts = {
        "Drug": 10,
        "RegulatoryAgency": 3,
        "RegulatoryApproval": 16,
        "Disease": 70,
        "Indication": 29,
        "Contraindication": 38,
        "OffLabelUse": 16,
        "AdverseSignal": 32,
        "AdverseEvent": 31,
        "Target": 14,
        "Protein": 22,
        "Pathway": 28,
    }
    if {key: counts[key] for key in expected_counts} != expected_counts:
        raise ValueError(f"Unexpected curated class breakdown: {counts}")
    entity_classes = {
        "drugs": ("drug_", ONTO.Drug),
        "approvals": ("approval_", ONTO.RegulatoryApproval),
        "diseases": ("disease_", ONTO.Disease),
        "adverse_events": ("ae_", ONTO.AdverseEvent),
        "adverse_signals": ("signal_", ONTO.AdverseSignal),
        "targets": ("target_", ONTO.Target),
        "proteins": ("protein_", ONTO.Protein),
        "pathways": ("pathway_", ONTO.Pathway),
    }
    for name, (prefix, class_) in entity_classes.items():
        actual = {
            str(subject)[len(str(RES)) + len(prefix):]
            for subject in graph.subjects(RDF.type, class_)
        }
        expected = set(entities[name])
        if actual != expected:
            raise ValueError(f"Unexpected {name} IDs in the materialized graph.")
    agency_ids = {
        str(subject)[len(str(RES)) + len("agency_"):]
        for subject in graph.subjects(RDF.type, ONTO.RegulatoryAgency)
    }
    if agency_ids != {row["id"] for row in entities["agencies"]}:
        raise ValueError("Unexpected regulatory-agency IDs in the materialized graph.")
    for name, class_ in {
        "indication": ONTO.Indication,
        "contraindication": ONTO.Contraindication,
        "off_label_use": ONTO.OffLabelUse,
    }.items():
        actual = {
            str(subject)[len(str(RES)) + len("assoc_"):]
            for subject in graph.subjects(RDF.type, class_)
        }
        if actual != set(entities["associations"][name]):
            raise ValueError(f"Unexpected {name} association IDs in the materialized graph.")

    edge_properties = {
        "drug_approval": (ONTO.hasApproval, "drug_", "approval_"),
        "approval_agency": (ONTO.approvedBy, "approval_", "agency_"),
        "drug_association": (ONTO.hasAssociation, "drug_", "assoc_"),
        "association_disease": (ONTO.forDisease, "assoc_", "disease_"),
        "drug_adverse_signal": (ONTO.hasAdverseSignal, "drug_", "signal_"),
        "signal_event": (ONTO.reportsEvent, "signal_", "ae_"),
        "drug_target": (ONTO.targets, "drug_", "target_"),
        "target_protein": (ONTO.hasComponent, "target_", "protein_"),
        "protein_pathway": (ONTO.participatesIn, "protein_", "pathway_"),
    }
    for name, (predicate, left_prefix, right_prefix) in edge_properties.items():
        actual = resource_pairs(graph, predicate, left_prefix, right_prefix)
        expected = {tuple(pair) for pair in curated["edges"][name]}
        if actual != expected:
            raise ValueError(f"Unexpected {name} edges: {len(actual)} actual, {len(expected)} expected.")

    if len(graph) != curated["expected_triples"]:
        raise ValueError(
            f"Expected {curated['expected_triples']} asserted triples, materialized {len(graph)}."
        )
    with (WORK_DIR / "data_csv" / "adverse_signal.csv").open(
        encoding="utf-8", newline=""
    ) as stream:
        for row in csv.DictReader(stream):
            subject = RES[f"signal_{row['signal_id']}"]
            values = list(graph.objects(subject, ONTO.llrScore))
            if len(values) != 1 or str(values[0]) != row["llr"]:
                raise ValueError(f"LLR lexical precision mismatch for {subject}.")

    required_links = (
        *((class_, ONTO.forDisease) for class_ in association_types),
        (ONTO.RegulatoryApproval, ONTO.approvedBy),
        (ONTO.AdverseSignal, ONTO.reportsEvent),
        (ONTO.AdverseSignal, ONTO.llrScore),
        (ONTO.Target, ONTO.hasComponent),
    )
    for class_, predicate in required_links:
        missing = [
            subject for subject in set(graph.subjects(RDF.type, class_))
            if not any(graph.objects(subject, predicate))
        ]
        if missing:
            raise ValueError(
                f"{len(missing)} {class_.split('#')[-1]} resource(s) lack "
                f"required property {predicate.split('#')[-1]}."
            )
    return counts


def validate_inference_targets(graph: Graph) -> dict[str, int]:
    drugs = set(graph.subjects(RDF.type, ONTO.Drug))
    approved = {
        drug for drug in drugs if any(graph.objects(drug, ONTO.hasApproval))
    }
    signals = set(graph.subjects(RDF.type, ONTO.AdverseSignal))
    strong_signals = {
        signal
        for signal in signals
        if any(float(score) >= 100.0 for score in graph.objects(signal, ONTO.llrScore))
    }
    contraindications = set(graph.subjects(RDF.type, ONTO.Contraindication))
    indications = set(graph.subjects(RDF.type, ONTO.Indication))
    off_label_uses = set(graph.subjects(RDF.type, ONTO.OffLabelUse))
    high_risk = {
        drug
        for drug in approved
        if set(graph.objects(drug, ONTO.hasAssociation)) & contraindications
        and set(graph.objects(drug, ONTO.hasAdverseSignal)) & strong_signals
    }
    repurposed = {
        drug
        for drug in approved
        if set(graph.objects(drug, ONTO.hasAssociation)) & indications
        and set(graph.objects(drug, ONTO.hasAssociation)) & off_label_uses
    }
    complex_targets = {
        target
        for target in graph.subjects(RDF.type, ONTO.Target)
        if len(set(graph.objects(target, ONTO.hasComponent))) >= 2
    }
    imatinib_pathways = {
        pathway
        for target in graph.objects(RES["drug_1423"], ONTO.targets)
        for protein in graph.objects(target, ONTO.hasComponent)
        for pathway in graph.objects(protein, ONTO.participatesIn)
    }
    drug_names = {
        str(label)
        for drug in repurposed
        for label in graph.objects(drug, RDFS.label)
    }
    complex_target_ids = {
        str(target).removeprefix(str(RES) + "target_")
        for target in complex_targets
    }
    weak_signal_ids = {
        str(signal).removeprefix(str(RES) + "signal_")
        for signal in signals - strong_signals
    }
    counts = {
        "SmallMoleculeDrug": sum(
            1
            for drug in drugs
            if any(str(smiles) for smiles in graph.objects(drug, ONTO.smiles))
        ),
        "ApprovedDrug": len(approved),
        "HighRiskApprovedDrug": len(high_risk),
        "RepurposedApprovedDrug": len(repurposed),
        "StrongAdverseSignal": len(strong_signals),
        "ProteinComplexTarget": len(complex_targets),
        "ImatinibPathways": len(imatinib_pathways),
    }
    expected_counts = {
        "SmallMoleculeDrug": 9,
        "ApprovedDrug": 10,
        "HighRiskApprovedDrug": 9,
        "RepurposedApprovedDrug": 7,
        "StrongAdverseSignal": 30,
        "ProteinComplexTarget": 5,
        "ImatinibPathways": 8,
    }
    if counts != expected_counts:
        raise ValueError(f"Unexpected locally derived inference counts: {counts}")
    expected_repurposed = {
        "atorvastatin", "chloroquine", "ciprofloxacin", "diazepam",
        "losartan", "metformin", "omeprazole",
    }
    if drug_names != expected_repurposed:
        raise ValueError(f"Unexpected repurposed drug membership: {drug_names}")
    if complex_target_ids != {"2731", "2732", "2733", "2752", "2815"}:
        raise ValueError(f"Unexpected protein-complex targets: {complex_target_ids}")
    if weak_signal_ids != {"SIG029116", "SIG029117"}:
        raise ValueError(f"Unexpected signals below LLR 100: {weak_signal_ids}")
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()

    config = "[DataSource1]\nmappings: mapping.rml.ttl\n"
    previous_cwd = Path.cwd()
    try:
        os.chdir(WORK_DIR)
        graph = morph_kgc.materialize(config)
    finally:
        os.chdir(previous_cwd)

    restore_llr_lexical_forms(graph)
    counts = validate(graph)
    inference_counts = validate_inference_targets(graph)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    serialized = prefixed_turtle(graph)
    temporary.write_text(
        serialized.decode("utf-8") if isinstance(serialized, bytes) else serialized,
        encoding="utf-8",
    )
    serialized_graph = Graph().parse(temporary, format="turtle")
    validate(serialized_graph)
    validate_inference_targets(serialized_graph)
    temporary.replace(args.output)
    print(f"Materialized {len(graph):,} triples to {args.output}")
    for name, count in counts.items():
        print(f"  {name}: {count:,}")
    print("Locally verified inference targets:")
    for name, count in inference_counts.items():
        print(f"  {name}: {count:,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
