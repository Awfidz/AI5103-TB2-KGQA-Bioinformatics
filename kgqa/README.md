# Drug Discovery KGQA (Step 5)

A question-answering app that uses a **local LLM** (via [Ollama](https://ollama.com)) on top of the
pharmacotherapy and drug discovery knowledge graph. You ask a question in plain English, the LLM
translates it into SPARQL, the query runs on the KG (GraphDB or a local copy of the Turtle files),
and the LLM writes the answer **only from the returned rows**.

```
question ──► entity linking ──► LLM: question → SPARQL ──► validate ──► run on KG ──► LLM: rows → answer
                 (labels)            (schema + few-shot)     (read-only,     │
                                                              prefixes)      └─ error / no rows → feed back, retry
```

## Features

- **Streamlit GUI**: chat-style interface that shows the answer, the generated SPARQL, the result table,
  the recognised entities, every attempt and timings.
- **Grounded answers**: the LLM writes only a one-line introduction in the question's language
  (Indonesian or English); the result rows are listed verbatim underneath, so names and numbers always
  match the KG. Yes/no questions get a short Ya/Tidak (Yes/No) answer. Empty results give a fixed "no
  information" answer and make no LLM call.
- **Entity linking**: before generating SPARQL, the app matches drug, disease, adverse-event, target,
  protein, pathway and agency labels in the question (exact, fuzzy for typos such as *metfromin*, and
  partial such as *type 2 diabetes* → *Diabetes mellitus type 2*). It passes the exact labels and IRIs
  to the LLM.
- **Self-correction**: syntax errors, runtime errors and empty results are sent back to the LLM, which
  retries (3 attempts by default).
- **Safety**: only `SELECT`/`ASK` queries are executed. Generated `INSERT`/`DELETE` queries are rejected.
- **Switchable KG backend**: GraphDB over the SPARQL protocol, or an in-memory rdflib graph loaded from
  the Turtle files. `auto` uses GraphDB when it is running.

## Project layout

```
kgqa/
  app.py              Streamlit GUI
  evaluate.py         runs the competency questions + extra questions through the app, writes a report
  kgqa/config.py      settings (environment variables)
  kgqa/kg.py          KG backends: GraphDB endpoint and local rdflib graph
  kgqa/linker.py      entity linking on rdfs:label
  kgqa/prompts.py     schema description, few-shot examples, answer prompt
  kgqa/pipeline.py    question → SPARQL → results → answer, with retries
  kgqa/llm.py         Ollama HTTP client
  tests/              offline tests (fake LLM, no Ollama needed)
sparql/
  queries/            Step 3 queries: CQ01–CQ15, U1 INSERT, U2 DELETE, U3 DESCRIBE
  run_queries.py      runs them and writes the .txt results
  results/            one result file per query
  sparql_queries_and_results.txt   all queries + results (submission file)
```

## Setup (Windows, PowerShell)

### 1. Python environment

From the repository root (Python 3.10+):

```powershell
python -m venv .venv
```

```powershell
.venv\Scripts\python -m pip install -r kgqa\requirements.txt
```

### 2. Local LLM with Ollama

Install Ollama from <https://ollama.com/download>, then pull a model:

```powershell
ollama pull qwen2.5:7b
```

| Model | Download | Memory while answering | Notes |
| --- | --- | --- | --- |
| `qwen2.5:7b` (default) | ~4.7 GB | ~6 GB (part on a 4 GB GPU, the rest in RAM) | Best SPARQL quality on a laptop |
| `qwen2.5:3b` | ~1.9 GB | ~2.5 GB (fits in 4 GB VRAM) | Faster, makes more query mistakes |

The app uses a 4K-token context (`OLLAMA_NUM_CTX=4096`) to keep memory low. Ollama unloads the model
10 minutes after the last question (`OLLAMA_KEEP_ALIVE`). To free memory right away, run
`ollama stop qwen2.5:7b`.

### 3. Knowledge graph

**Option A: GraphDB.** Create a repository named `drug-kgqa`, import
`ontology/drug_discovery.ttl` and the materialised KG from Step 4, and keep GraphDB running on port 7200.
To limit memory, start GraphDB with a smaller heap (e.g. `-Xmx2g`).
To reproduce the curated Step 4 graph, follow [`kg_population/README.md`](../kg_population/README.md).

**Option B: local files (no GraphDB).** The app loads `ontology/drug_discovery.ttl` plus every `kg/*.ttl`
file if that folder exists. Use `KG_FILES` to point at other files.

## Run

```powershell
.venv\Scripts\streamlit run kgqa\app.py
```

Open <http://localhost:8501>. Pick the model and KG backend in the sidebar, then type a question or click
an example.

Run the Step 3 queries and regenerate the result files:

```powershell
.venv\Scripts\python sparql\run_queries.py
```

The INSERT and DELETE queries run on an in-memory copy of the KG, with a verification query before and
after.

Evaluate the app (Ollama must be running). It asks the 15 competency questions, as written in the query
headers, plus 6 extra questions, and writes `kgqa\evaluation\eval_<model>_<lang>.md`. A full run takes
about 15–20 minutes on the laptop below.

```powershell
.venv\Scripts\python kgqa\evaluate.py
```

Use `--lang en` to ask the English versions of the CQs, and `--only CQ03,CQ10` to run a subset.

Offline tests (no Ollama needed):

```powershell
.venv\Scripts\python -m pytest kgqa\tests -q
```

## Configuration

All settings are environment variables, e.g. `$env:OLLAMA_MODEL = "qwen2.5:3b"` in PowerShell.

| Variable | Default | Meaning |
| --- | --- | --- |
| `KG_BACKEND` | `auto` | `auto`, `graphdb` or `local` |
| `GRAPHDB_URL` | `http://localhost:7200` | GraphDB server |
| `GRAPHDB_REPO` | `drug-kgqa` | GraphDB repository id |
| `KG_FILES` | ontology + `kg/*.ttl` | Turtle files for the local backend (`;`-separated) |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama server |
| `OLLAMA_MODEL` | `qwen2.5:7b` | Model used for SPARQL and answers |
| `OLLAMA_NUM_CTX` | `4096` | Context window (larger needs more memory) |
| `OLLAMA_KEEP_ALIVE` | `10m` | How long the model stays loaded after a question |
| `KGQA_MAX_ATTEMPTS` | `3` | SPARQL generation attempts per question |
| `KGQA_MAX_ROWS` | `50` | Rows passed to the answer step |

## Example questions

The competency questions work as they are, in Indonesian or English, for example:

- Lembaga regulator apa saja yang telah menyetujui sildenafil, beserta tanggal persetujuannya?
- Is ciprofloxacin indicated for typhoid fever, contraindicated in epilepsy, and does it have a strong
  adverse signal for tendon pain?
- Apakah trastuzumab tergolong obat berizin dengan risiko keamanan tinggi?
- Which Reactome pathways are affected by imatinib's mechanism of action?
- Obat apa saja yang dikontraindikasikan pada pasien dengan Hepatic failure?
- What are the three strongest adverse event signals for diazepam?

## Capabilities and limitations

What it handles:

- Questions that follow the ontology's paths: indications, contraindications, off-label use, adverse
  signals with LLR scores, approvals by agency and date, targets, protein subunits, pathways.
- Filters, rankings and aggregates (e.g. "before 1990", "top 3", "most contraindications", counts).
- Yes/no questions, answered with an `ASK` query; the answer starts with Yes/No (Ya/Tidak).
- Questions in Indonesian, answered in Indonesian (the KG labels themselves are English).
- Misspelled or partial entity names, through entity linking.
- Defined classes and the property chain (`HighRiskApprovedDrug`, `SmallMoleculeDrug`, `affectsPathway`,
  ...) when the prompt spells out their conditions, so no reasoner is needed.

Known limitations:

- **Synonyms**: names are matched on `rdfs:label` only. "High cholesterol" is not linked to
  *Hypercholesterolemia* unless the LLM makes that connection itself.
- **Small-model errors**: a 3B–7B model sometimes writes wrong paths (e.g. a direct drug→disease link) or
  invents properties. Retries fix many of these but not all. Check the generated SPARQL shown in the UI.
- **Coverage**: the app can only answer what is in the KG. Questions about doses, mechanisms in free text
  or anything outside the ontology get "no information", or an answer that only partly fits.
- **No reasoning in the local backend**: inferred types are not materialised in rdflib. The prompt
  compensates, but a question phrased only in terms of an inferred class can still fail.
- **Badly shaped results on complex questions**: for multi-condition questions the model may return
  every combination instead of one row per drug, or leave out the drug column. The query results are still
  right, but the written answer can then be incomplete or misleading (see CQ04 and CQ05 below).
- **Long multi-condition questions**: Scenario CQs (several conditions in one long Indonesian
  sentence) are the hardest. The model can add conditions nobody asked for (an agency or date, an extra
  event), nest `FILTER`s badly, or group results wrongly.
- **Prompt sensitivity**: a 7B model copies details from the few-shot examples. An example about "EMA
  approvals since 2000" made it add EMA and date filters to unrelated questions. Adding more rules and a
  glossary to the prompt also made results *worse*, so the prompt is kept short and fixed mistakes are
  repaired in code instead (see the table below).
- **Ties are hidden**: "which drug has the most ..." uses `LIMIT 1`, so a tie (imatinib and metformin both
  have 6 contraindications) shows only one drug.
- **Latency** (laptop: i7-10750H, GTX 1650 4 GB, `qwen2.5:7b` with ~2.3 GB on the GPU and the rest on the
  CPU, about 5 tokens/s): 20–40 s for a short question, 1–2 minutes for the long scenario CQs, and up to
  ~4 minutes when all three attempts are needed. The first question after the model loads takes about 2
  minutes longer.
- **Not medical advice**: the data comes from DrugCentral, FAERS, UniProt and Reactome and is for
  coursework only.

## Measured results

From `kgqa/evaluation/eval_qwen2.5_7b_id.md` (local backend, 10-drug KG in the ontology file,
2026-11-21, total 13 minutes). The 15 CQs were asked exactly as written in Indonesian. "Answer" is
whether the written answer states every expected item (or the right Ya/Tidak):

| CQ | Topic | Query result | Answer |
| --- | --- | --- | --- |
| CQ01 | Sildenafil approvals and dates | Correct | Complete |
| CQ02 | Multi-protein targets of diazepam / omeprazole | Verbose: right targets, 11 rows (one per protein) | Complete |
| CQ03 | Diazepam: indication + contraindication + high-risk (yes/no) | **Wrong**: the `ASK` added an invented condition | Says Tidak (expected Ya) |
| CQ04 | Ciprofloxacin: typhoid / epilepsy / tendon pain (yes/no) | Correct | Ya |
| CQ05 | Is trastuzumab high-risk? (yes/no) | Correct | Tidak |
| CQ06 | High-risk small molecule for T2DM vs. acute infection | **Wrong** this run (correct in 2 of the 4 development runs) | No information |
| CQ07 | Hypercholesterolemia / muscle disorder / myalgia | Correct (atorvastatin) | Complete |
| CQ08 | Indicated for hypertension, off-label for heart failure | Correct (losartan) | Complete |
| CQ09 | Pathways affected by imatinib | Correct (8 pathways) | Complete |
| CQ10 | Chloroquine safety profile | Partial: 3 of 4 expected items | 3 of 4 |
| CQ11 | Drugs contraindicated in hepatic failure | Correct | Complete |
| CQ12 | Top 3 adverse signals of diazepam | Correct | Complete |
| CQ13 | FDA approvals before 1990 | Correct | Complete |
| CQ14 | Small molecules under 500 Da | Correct | Complete |
| CQ15 | All high-risk approved drugs with counts | Partial: grouped wrongly, 1 of 9 drugs | 1 of 9 |

**Queries: 10/15 correct**, 1 verbose, 2 partial, 2 wrong. **Written answers: 11/15 complete, all 15 in
Indonesian.**

Extra questions:

| Question | Result |
| --- | --- |
| Typo ("metfromin") | Correct, via fuzzy entity linking |
| Indonesian ("Apa saja kontraindikasi dari omeprazole?") | Correct, answered in Indonesian |
| Multi-hop (drug → target → protein → pathway) | Correct (diazepam) |
| Aggregation ("most contraindications") | Correct (imatinib; the tie with metformin is hidden by `LIMIT 1`) |
| Synonym ("high cholesterol") | Not answered: no label match for *Hypercholesterolemia* |
| Out of scope (dose) | Correctly says the KG has no information |

**How answers are written.** When the model wrote whole answers itself (runs 1–4), it dropped items,
translated entity names ("Completed suicide" became "Kompleks suicide"), invented LLR values, and answered
Indonesian questions in English. Now the model writes only a one-line introduction in the question's
language (cut at the first colon), and the app appends the result rows verbatim. Names and numbers in the
answer always match the KG, so a correct query always gives a complete answer. Yes/no questions still get
a short Ya/Tidak answer written by the model.

The remaining failures are all on the query side: an invented extra condition in an `ASK` (CQ03), wrong
grouping (CQ15), only part of a long multi-part question answered (CQ10), and run-to-run variation (CQ06).

Rule-based repairs in `pipeline.py` fix mistakes the model made repeatedly during development:

| Model mistake | Repair |
| --- | --- |
| Compares string dates with `xsd:date` / `YEAR()` | Rewritten to ISO string comparisons |
| Writes `:rdfs:label` | Rewritten to `rdfs:label` |
| Puts `COUNT` inside `FILTER` | Moved into `GROUP BY ... HAVING` |
| Matches `rdfs:label "Exact Name"` (no `@en`, case-sensitive) | Variable plus case-insensitive `FILTER` |
| Selects or counts a variable that WHERE never binds (`?contra` vs `?contraAssoc`, `?approvalDate` vs `?date`) | Renamed to the obvious bound variable; unmatched plain columns dropped; otherwise rejected with the list of bound variables |
| Writes `"x"^^xsd:string` | Typed string turned into a plain literal (same value in RDF 1.1) |
| Writes `?disease rdfs:label ?disease` | Label variable renamed to `?diseaseName` |
| Returns rows with empty columns | Sent back to the model as an error |
