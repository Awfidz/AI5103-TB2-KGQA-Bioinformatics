"""Prompts for the two LLM calls: question -> SPARQL, and results -> answer.

The schema description is written by hand from ontology/drug_discovery.ttl.
It is deliberately short (the model runs with a 4K-token context) and spells
out the patterns small models get wrong: reified drug-disease associations,
language-tagged labels, and defined classes that are not materialised.
"""

from __future__ import annotations

from .config import prefix_block

SCHEMA = """\
Knowledge graph: pharmacotherapy and drug discovery (DrugCentral, FAERS, UniProt, Reactome).
Ontology prefix ":" = <https://itb.ac.id/a5103/tubes_2#>, instances use "res:".
Drugs, diseases, adverse events, targets, proteins, pathways and agencies have an English rdfs:label
(e.g. "metformin"@en). Associations, adverse signals and approvals have NO label: use the label of the
disease, event or agency they point to.

Classes and how they connect (subject --property--> object):
  :Drug --:hasAssociation--> :DrugDiseaseAssociation --:forDisease--> :Disease
      association types: :Indication (approved use), :Contraindication, :OffLabelUse
  :Drug --:hasAdverseSignal--> :AdverseSignal --:reportsEvent--> :AdverseEvent
      :AdverseSignal has :llrScore (xsd:double, FAERS log-likelihood ratio; >= 100 = strong signal)
  :Drug --:hasApproval--> :RegulatoryApproval --:approvedBy--> :RegulatoryAgency (labels "FDA", "EMA", "PMDA")
      :RegulatoryApproval has :approvalDate (string "YYYY-MM-DD"; compare as string, e.g. STR(?d) < "1990-01-01")
  :Drug --:targets--> :Target --:hasComponent--> :Protein --:participatesIn--> :Pathway (Reactome)
      :Protein has :uniprotAccession (string)
  :Drug has :molecularWeight (xsd:double, Dalton) and :smiles (string, only small molecules)

Defined classes are NOT stored as types; express them with their conditions:
  approved drug          = ?drug :hasApproval ?ap
  strong adverse signal  = ?signal :llrScore ?llr . FILTER(?llr >= 100)
  small-molecule drug    = ?drug :smiles ?s          (biologics have no :smiles)
  protein complex target = target with >= 2 :hasComponent proteins
  drug affects pathway   = ?drug :targets/:hasComponent/:participatesIn ?pathway
  high-risk approved drug  = approved + some :Contraindication association + a strong adverse signal
  repurposed approved drug = approved + some :Indication association + some :OffLabelUse association
"""

RULES = """\
Rules:
1. Write ONE SPARQL 1.1 query: SELECT, or ASK for yes/no questions ("Is ...?", "Does ...?", "Apakah ...?").
   Never INSERT/DELETE. Use only the classes and properties above.
2. Drugs and diseases are NOT linked directly: always go through ?drug :hasAssociation ?a . ?a a :Indication ; :forDisease ?disease .
3. Match names case-insensitively on labels: ?x rdfs:label ?name . FILTER(LCASE(STR(?name)) = "metformin")
   If entity IRIs are listed under "Entities found in the question", you may use those IRIs directly.
4. Return human-readable labels (e.g. ?drugName), not only IRIs, and only the columns the question needs;
   include the drug name whenever results belong to different drugs. Use DISTINCT.
5. Add ORDER BY for rankings and LIMIT when the question asks for "top"/"strongest"/"most".
6. Conditions on counts need GROUP BY + HAVING (COUNT(DISTINCT ?x) >= n); never put COUNT inside FILTER.
7. When one drug needs two different associations (e.g. an indication AND an off-label use), give each its
   own variables (?ind ?indDisease, ?off ?offDisease); do not reuse one ?disease for both.
8. Every variable in SELECT must be bound in WHERE (e.g. ?drug rdfs:label ?drugName).
9. For yes/no questions with several conditions, put every condition in one ASK pattern. Add only the
   conditions the question states; never invent agencies, dates or events.
10. FILTER(...) holds conditions only. Triple patterns (?s :p ?o) go outside FILTER.
11. Reply with the query only, inside a ```sparql code block.
"""

# Few-shot examples. They use different entities and question shapes from the
# competency questions in sparql/queries, so evaluation on those is not leaked.
EXAMPLES = [
    (
        "What is sildenafil used to treat off-label?",
        """SELECT DISTINCT ?diseaseName WHERE {
  ?drug rdfs:label ?drugName ; :hasAssociation ?a .
  FILTER(LCASE(STR(?drugName)) = "sildenafil")
  ?a a :OffLabelUse ; :forDisease ?disease .
  ?disease rdfs:label ?diseaseName .
}""",
    ),
    (
        "Which drugs report rhabdomyolysis as an adverse event, and how strong is the signal?",
        """SELECT DISTINCT ?drugName ?llr WHERE {
  ?event rdfs:label ?eventName .
  FILTER(LCASE(STR(?eventName)) = "rhabdomyolysis")
  ?signal :reportsEvent ?event ; :llrScore ?llr .
  ?drug :hasAdverseSignal ?signal ; rdfs:label ?drugName .
} ORDER BY DESC(?llr)""",
    ),
    (
        "Which proteins make up the target of omeprazole, and what are their UniProt accessions?",
        """SELECT DISTINCT ?targetName ?proteinName ?accession WHERE {
  ?drug rdfs:label ?drugName ; :targets ?target .
  FILTER(LCASE(STR(?drugName)) = "omeprazole")
  ?target rdfs:label ?targetName ; :hasComponent ?protein .
  ?protein rdfs:label ?proteinName ; :uniprotAccession ?accession .
}""",
    ),
    (
        "Is atorvastatin contraindicated in hypothyroidism, and does it have any strong adverse signal?",
        """ASK {
  ?drug rdfs:label ?drugName ; :hasAssociation ?ci ; :hasAdverseSignal ?signal .
  FILTER(LCASE(STR(?drugName)) = "atorvastatin")
  ?ci a :Contraindication ; :forDisease/rdfs:label ?ciDisease .
  FILTER(LCASE(STR(?ciDisease)) = "hypothyroidism")
  ?signal :llrScore ?llr .
  FILTER(?llr >= 100)
}""",
    ),
    (
        "Which adverse event is reported for the most drugs?",
        """SELECT ?eventName (COUNT(DISTINCT ?drug) AS ?numberOfDrugs) WHERE {
  ?drug :hasAdverseSignal ?signal .
  ?signal :reportsEvent ?event .
  ?event rdfs:label ?eventName .
}
GROUP BY ?eventName
ORDER BY DESC(?numberOfDrugs)
LIMIT 1""",
    ),
]


def sparql_system_prompt() -> str:
    return (
        "You translate questions about a drug knowledge graph into SPARQL queries.\n\n"
        + SCHEMA
        + "\nPrefixes (already declared, you may omit them):\n"
        + prefix_block()
        + "\n\n"
        + RULES
    )


def sparql_messages(question: str, entity_hints: list[str]) -> list[dict]:
    messages = [{"role": "system", "content": sparql_system_prompt()}]
    for q, sparql in EXAMPLES:
        messages.append({"role": "user", "content": f"Question: {q}"})
        messages.append({"role": "assistant", "content": f"```sparql\n{sparql}\n```"})
    content = f"Question: {question}"
    if entity_hints:
        content += "\n\nEntities found in the question:\n" + "\n".join(f"- {h}" for h in entity_hints)
    messages.append({"role": "user", "content": content})
    return messages


def repair_message(problem: str) -> dict:
    return {
        "role": "user",
        "content": (
            f"{problem}\n"
            "Re-check the schema: drug-disease links go through :hasAssociation / :forDisease, "
            "adverse events through :hasAdverseSignal / :reportsEvent, and names must be matched "
            "with LCASE(STR(?label)). Return a corrected query in a ```sparql code block."
        ),
    }


ANSWER_SYSTEM = """\
You write a short answer to a question about drugs, based ONLY on the knowledge-graph results given.
- Do not add facts, numbers, reasons or medical advice that are not in the results.
- Keep drug, disease and other names exactly as written in the results; never translate them."""

_ID_WORDS = {
    "apa", "apakah", "yang", "dan", "untuk", "dengan", "obat", "saja", "beserta", "dari", "pada", "seorang",
    "pasien", "berapa", "bagaimana", "mana", "adalah", "tidak", "ini", "itu", "diindikasikan", "kontraindikasi",
    "dikontraindikasikan", "sinyal", "efek", "samping", "berizin", "disetujui", "jalur", "tergolong", "memiliki",
}
_YES_NO_START = ("is ", "are ", "does ", "do ", "did ", "can ", "has ", "have ", "was ", "were ", "apakah ")


def is_indonesian(text: str) -> bool:
    words = {w.strip(".,?!()").lower() for w in text.split()}
    return len(words & _ID_WORDS) >= 2


def is_yes_no(question: str, form: str) -> bool:
    if form == "ASK":
        return True
    q = question.strip().lower()
    # Scenario questions put the yes/no question last ("Seorang pasien ... Apakah ...?").
    last = q.rstrip("?").split(". ")[-1]
    return q.startswith(_YES_NO_START) or last.startswith(_YES_NO_START)


def answer_messages(question: str, sparql: str, table: str, truncated: bool, form: str = "SELECT",
                    n_rows: int = 0) -> list[dict]:
    """Prompt for the answer step.

    Yes/no questions get a full short answer that starts with Yes/No (Ya/Tidak). For every other
    question the model writes ONE introductory sentence only; the pipeline appends the result rows
    itself, so names and numbers are never dropped, translated or invented.
    """
    indonesian = is_indonesian(question)
    yes, no = ("Ya", "Tidak") if indonesian else ("Yes", "No")
    language = "Indonesian (Bahasa Indonesia)" if indonesian else "English"
    if is_yes_no(question, form):
        task = (f'This is a yes/no question. A result of "yes" or "true" means {yes}; "no" or "false" means {no}. '
                f'Answer in one or two sentences in {language}, starting with "{yes}" or "{no}". If the answer is '
                f"{no}, say that not all conditions in the question hold; do not guess which one failed unless "
                "the results show it.")
    else:
        task = (f"The {n_rows} result row(s) above answer the question and will be shown to the user as a list "
                f"right after your sentence. Write ONE short sentence in {language} that introduces them and "
                "ends with a colon. Do not name any of the items and do not mention any numbers.")
    note = "\n(Only the first rows are shown.)" if truncated else ""
    query = "\n".join(line for line in sparql.splitlines() if not line.upper().startswith("PREFIX"))
    return [
        {"role": "system", "content": ANSWER_SYSTEM},
        {
            "role": "user",
            "content": f"Question: {question}\n\nSPARQL query used:\n{query}\n\nResults:\n{table}{note}\n\n{task}",
        },
    ]
