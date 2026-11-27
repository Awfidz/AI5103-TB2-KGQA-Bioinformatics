# KG Population (Step 4)

This pipeline exports curated CSV sources from `dataset/json/` and materializes
the asserted ABox through `mapping.rml.ttl`. `curated_ids.json` is the static
manifest of individual IDs, agency labels, and curated relation pairs extracted
from the current source ontology. Preprocessing reads only the dataset JSON and
that manifest; it does not parse or regex the ontology at runtime.

## Run from the repository root

```bash
python -m pip install -r kg_population/requirements.txt
python -m kg_population.prepare_csv
python -m kg_population.run_rml
python -m kg_population.verify_step4   # xlsx + materialized ABox + local inference checks
```

Both modules resolve inputs and mappings relative to their own location, so the
commands are also independent of the caller's working directory. Preprocessing
writes exactly 17 files under `kg_population/data_csv/`. It selects 14 drug-target
edges from the curated manifest without filtering on `moa`, including
`drug_607 -> target_5515`; and selects the 45 curated protein-pathway edges,
excluding `(P04626, R-HSA-1257604)`.

Morph-KGC writes the asserted graph to `kg/drug_discovery_kg.ttl`. The
materializer verifies the exact individual triples, literal lexical forms,
309-entity class breakdown, and edge counts (14 `targets`, 25 `hasComponent`,
45 `participatesIn`). It also locally checks the specified derived-class
memberships and the 8 imatinib pathways. The asserted output remains free of
inferred class assertions. The output is prefixed Turtle (`:` and `res:`); `xsd:double` lexical forms are preserved.

## GraphDB

Create an **empty** GraphDB repository with the `OWL2-RL (Optimized)` ruleset.
Then set `GRAPHDB_URL` and `GRAPHDB_REPO` if needed and run:

```bash
python -m kg_population.materialize_graphdb
```

The script imports the TBox `ontology/drug_discovery.ttl` and the asserted
`kg/drug_discovery_kg.ttl`, applies the four `INSERT` updates in
`graphdb_materialize.sparql` (one request each, in order), validates the counts, and exports the final graph
to `kg_population/graphdb_export/drug_discovery_graphdb_final.ttl`.
`graphdb_sanity_check.sparql` contains the manual check (targets 9 / 10 / 9 / 7 / 30 / 5 / 8). RML mappings
remain primitive; the SPARQL updates materialize only `SmallMoleculeDrug`, `StrongAdverseSignal`,
`HighRiskApprovedDrug` and `ProteinComplexTarget` (cases OWL2-RL Optimized does
not evaluate). `ApprovedDrug`, `RepurposedApprovedDrug` and `affectsPathway`
(imatinib: 8) are left to the reasoner.

The Morph-KGC asserted file is not a GraphDB export. A final GraphDB export is a
separate repository snapshot containing the TBox, asserted ABox, and inference
results. The materialization script requires an empty repository to avoid stale
triples and does not claim remote validation unless GraphDB is reachable.

The active source ontology is a TBox without named individuals or the unused
`res:` prefix. OOPS P41 reports that the ontology is missing `dct:license`;
that source metadata issue is noted here and is intentionally not changed as
part of Step 4.

The local KGQA backend loads the source ontology and all Turtle files in `kg/`.
To test it explicitly, set `KG_BACKEND=local` when launching KGQA. To use
GraphDB, import the TBox and asserted ABox into the repository configured by
`GRAPHDB_REPO` (default: `drug-kgqa`) before running the inference updates.
