"""Offline tests: run without Ollama by replacing the LLM with a scripted fake.

    .venv\\Scripts\\python -m pytest kgqa\\tests -q
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kgqa.config import Settings  # noqa: E402
from kgqa.kg import LocalKG, query_form  # noqa: E402
from kgqa.linker import EntityLinker  # noqa: E402
from kgqa.pipeline import KGQA, NO_RESULTS_ANSWER, extract_sparql, prepare_query  # noqa: E402
from kgqa.prompts import EXAMPLES  # noqa: E402

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def kg():
    return LocalKG([
        REPO / "ontology" / "drug_discovery.ttl",
        REPO / "kg" / "drug_discovery_kg.ttl",
    ])


@pytest.fixture(scope="module")
def linker(kg):
    return EntityLinker(kg)


class FakeLLM:
    """Returns scripted replies in order and records the prompts it received."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def chat(self, messages, temperature=0.0, max_tokens=700):
        self.calls.append([dict(m) for m in messages])  # snapshot: the pipeline keeps appending
        return self.replies.pop(0)


def settings():
    s = Settings()
    s.max_attempts = 3
    return s


@pytest.mark.parametrize("question,sparql", EXAMPLES)
def test_few_shot_examples_are_valid(kg, question, sparql):
    form, res = kg.run(prepare_query(sparql, 50))
    assert form in {"SELECT", "ASK"}
    if form == "SELECT":
        assert res.variables


def test_pipeline_answers_yes_no_with_ask(kg, linker):
    ask = """```sparql
ASK {
  ?drug rdfs:label ?n ; :hasAssociation ?a .
  FILTER(LCASE(STR(?n)) = "trastuzumab")
  ?a a :Contraindication .
}
```"""
    llm = FakeLLM([ask, "No, trastuzumab has no recorded contraindication."])
    out = KGQA(kg, llm, settings(), linker).ask("Does trastuzumab have a contraindication?")
    assert out.ok and len(out.attempts) == 1
    assert [str(r["answer"]) for r in out.result.rows] == ["no"]
    assert out.answer.startswith("No")


def test_query_form():
    assert query_form("PREFIX : <http://x#>\n# c\nselect * {}") == "SELECT"
    assert query_form("PREFIX a: <http://x/#frag>\nDELETE WHERE { ?s ?p ?o }") == "UPDATE"
    assert query_form("DESCRIBE <http://x>") == "DESCRIBE"


def test_linker_exact_and_fuzzy(linker):
    labels = {m.entity.label for m in linker.link("What is metfromin indicated for?")}
    assert "metformin" in labels
    labels = {m.entity.label for m in linker.link("drugs contraindicated in hepatic failure")}
    assert "Hepatic failure" in labels
    labels = {m.entity.label for m in linker.link("Who approved Imatinib at the FDA?")}
    assert {"imatinib", "FDA"} <= labels


def test_extract_and_prepare():
    reply = "Here you go:\n```sparql\nSELECT ?n WHERE { ?d rdfs:label ?n }\n```"
    q = extract_sparql(reply)
    assert q.startswith("SELECT")
    prepared = prepare_query(q, max_rows=50)
    assert "PREFIX rdfs:" in prepared and "LIMIT 200" in prepared


def test_date_filters_are_rewritten_to_strings(kg):
    raw = """SELECT ?n ?d WHERE { ?x rdfs:label ?n ; :hasApproval/:approvalDate ?d .
      FILTER(?d < "1990-01-01"^^xsd:date && xsd:date(?d) > "1950-01-01"^^xsd:date && YEAR(?d) > 1950) }"""
    q = prepare_query(raw, 50)
    assert "^^xsd:date" not in q and "YEAR(" not in q
    names = {str(r["n"]) for r in kg.select(q).rows}
    # 1950-1990, any agency: diazepam 1963, metformin 1961 (PMDA), ciprofloxacin 1987, omeprazole 1989
    assert names == {"diazepam", "metformin", "ciprofloxacin", "omeprazole"}


def test_double_prefix_is_fixed(kg):
    # Real model output (CQ06): ":rdfs:label" is a legal but wrong IRI.
    raw = """SELECT DISTINCT ?approvalDate ?agencyName WHERE {
  res:drug_1423 :rdfs:label "imatinib"@en ; :hasApproval ?approval .
  ?approval :approvedBy ?agency ; :approvalDate ?approvalDate .
  ?agency rdfs:label ?agencyName . }"""
    rows = kg.select(prepare_query(raw, 50)).rows
    assert {str(r["agencyName"]) for r in rows} == {"FDA", "EMA"}


@pytest.mark.parametrize("raw", [
    # Real model outputs (CQ08): COUNT inside FILTER, with and without a HAVING already present.
    """SELECT DISTINCT ?targetName WHERE {
  ?target rdfs:label ?targetName ; :hasComponent ?protein .
  FILTER (COUNT(?protein) >= 2)
}""",
    """SELECT DISTINCT ?targetName WHERE {
  ?drug :targets ?target .
  ?target :hasComponent ?protein .
  FILTER (COUNT(DISTINCT ?protein) >= 2)
  ?target rdfs:label ?targetName .
}
GROUP BY ?targetName
HAVING (COUNT(DISTINCT ?protein) >= 2)""",
])
def test_aggregate_filter_moves_to_having(kg, raw):
    rows = kg.select(prepare_query(raw, 50)).rows
    assert len(rows) == 5


def test_unbound_column_triggers_retry(kg, linker):
    unbound = """```sparql
SELECT DISTINCT ?drugName WHERE {
  ?drug :hasApproval ?ap .
  ?ap :approvedBy res:agency_fda ; :approvalDate ?date .
  FILTER(STR(?date) < "1990-01-01")
}
```"""
    good = """```sparql
SELECT DISTINCT ?drugName WHERE {
  ?drug rdfs:label ?drugName ; :hasApproval ?ap .
  ?ap :approvedBy res:agency_fda ; :approvalDate ?date .
  FILTER(STR(?date) < "1990-01-01")
}
```"""
    llm = FakeLLM([unbound, good, "Four drugs."])
    out = KGQA(kg, llm, settings(), linker).ask("FDA approvals before 1990")
    assert out.ok and len(out.result) == 4
    assert "never bound" in out.attempts[0].error


def test_label_literals_match_case_and_language_insensitively(kg):
    raw = """SELECT DISTINCT ?drugName WHERE {
  ?drug rdfs:label ?drugName ; :targets ?target .
  ?target :hasComponent ?protein .
  ?protein :participatesIn ?pathway .
  ?pathway rdfs:label "GABA Receptor Activation" .
}"""
    rows = kg.select(prepare_query(raw, 50)).rows
    assert {str(r["drugName"]) for r in rows} == {"diazepam"}


def test_label_literal_inside_predicate_list(kg):
    raw = 'SELECT ?d WHERE { ?x rdfs:label "Imatinib"@en ; :hasApproval/:approvalDate ?d . }'
    assert len(kg.select(prepare_query(raw, 50)).rows) == 2


def test_misnamed_variable_is_renamed(kg):
    raw = """SELECT DISTINCT ?agencyName ?approvalDate WHERE {
  res:drug_2441 :hasApproval ?approval .
  ?approval :approvedBy ?agency ; :approvalDate ?date .
  ?agency rdfs:label ?agencyName .
}
ORDER BY ?approvalDate"""
    rows = kg.select(prepare_query(raw, 50)).as_text_rows()
    assert rows == [{"agencyName": "FDA", "date": "1998-03-27"}, {"agencyName": "EMA", "date": "1998-09-13"}]


def test_misnamed_aggregate_variable_is_renamed(kg):
    raw = """SELECT ?drugName (COUNT(DISTINCT ?contra) AS ?n) WHERE {
  ?drug rdfs:label ?drugName ; :hasAssociation ?contraAssoc .
  ?contraAssoc a :Contraindication .
} GROUP BY ?drugName ORDER BY DESC(?n) ?drugName"""
    rows = kg.select(prepare_query(raw, 50)).as_text_rows()
    assert rows[0] == {"drugName": "imatinib", "n": "6"}


def test_unmatched_unbound_columns_are_dropped(kg):
    raw = """SELECT DISTINCT ?riskStatus ?contraindication ?eventName WHERE {
  ?drug rdfs:label ?drugName ; :hasAssociation ?contraindicationAssoc ; :hasAdverseSignal ?s .
  FILTER(LCASE(STR(?drugName)) = "chloroquine")
  ?contraindicationAssoc a :Contraindication ; :forDisease ?contraindicationDisease .
  ?contraindicationDisease rdfs:label ?contraindicationDiseaseName .
  ?s :reportsEvent/rdfs:label ?eventName ; :llrScore ?llr . FILTER(?llr >= 100)
}"""
    q = prepare_query(raw, 50)
    res = kg.select(q)
    assert res.variables == ["contraindicationDiseaseName", "eventName"]
    assert len(res.rows) == 9  # 3 contraindications x 3 strong signals


def test_typed_string_literals_and_self_labels_are_fixed(kg):
    raw = """ASK {
  ?drug rdfs:label ?drugName ; :hasAssociation ?ind .
  FILTER(LCASE(STR(?drugName)) = "diazepam"^^xsd:string)
  ?ind a :Indication ; :forDisease ?indicationDisease .
  ?indicationDisease rdfs:label ?indicationDisease .
  FILTER(LCASE(STR(?indicationDiseaseName)) = "alcohol withdrawal syndrome"^^xsd:string)
}"""
    q = prepare_query(raw, 50)
    assert "^^xsd:string" not in q and "rdfs:label ?indicationDiseaseName" in q
    assert kg.ask(q) is True


def test_unbound_aggregate_variable_is_rejected():
    raw = """SELECT DISTINCT ?drugName (COUNT(DISTINCT ?contraindication) AS ?n) WHERE {
  ?drug rdfs:label ?drugName ; :hasAssociation ?association .
  ?association a :Contraindication .
} GROUP BY ?drugName ORDER BY DESC(?n) LIMIT 1"""
    with pytest.raises(ValueError, match="contraindication"):
        prepare_query(raw, 50)


def test_answer_prompt_language_and_yes_no():
    from kgqa.prompts import answer_messages, is_indonesian, is_yes_no

    cq03 = ("Seorang pasien datang dengan Alcohol withdrawal syndrome. Apakah diazepam diindikasikan resmi "
            "untuk kondisi pertama?")
    assert is_indonesian(cq03) and is_yes_no(cq03, "SELECT")
    assert not is_indonesian("Which drug has the most contraindications?")
    assert not is_yes_no("Which drug has the most contraindications?", "SELECT")
    assert is_yes_no("Which drugs ...", "ASK")

    msg = answer_messages(cq03, "PREFIX : <x>\nASK {}", "answer\n------\nyes", False, "ASK", 1)[-1]["content"]
    assert 'starting with "Ya" or "Tidak"' in msg and "Indonesian" in msg and "PREFIX" not in msg
    msg = answer_messages("Which drug has the most contraindications?", "SELECT", "t", False, "SELECT", 1)[-1]["content"]
    assert "Write ONE short sentence in English" in msg


def test_lead_sentence_is_trimmed():
    from kgqa.pipeline import lead_sentence

    assert lead_sentence("Ini tiga sinyal terkuat untuk diazepam: penggunaan obat, keracunan") == \
        "Ini tiga sinyal terkuat untuk diazepam:"
    assert lead_sentence("These are the contraindications of omeprazole. They include x.") == \
        "These are the contraindications of omeprazole:"
    assert lead_sentence("- Kontraindikasi omeprazole adalah") == "Kontraindikasi omeprazole adalah:"


def test_list_answers_append_rows_verbatim(kg, linker):
    sparql = """```sparql
SELECT ?drugName ?approvalDate WHERE {
  ?drug rdfs:label ?drugName ; :hasApproval ?ap .
  ?ap :approvedBy/rdfs:label "FDA" ; :approvalDate ?approvalDate .
  FILTER(STR(?approvalDate) < "1990-01-01")
} ORDER BY ?approvalDate
```"""
    llm = FakeLLM([sparql, "Obat berikut disetujui FDA sebelum 1990:\nextra line that must be dropped"])
    out = KGQA(kg, llm, settings(), linker).ask("Obat apa saja yang disetujui oleh FDA sebelum tahun 1990?")
    assert out.answer.splitlines()[0] == "Obat berikut disetujui FDA sebelum 1990:"
    assert "- chloroquine (approval date: 1949-10-31)" in out.answer
    assert "- omeprazole (approval date: 1989-09-14)" in out.answer
    assert "extra line" not in out.answer


def test_rejects_updates():
    with pytest.raises(ValueError):
        prepare_query("DELETE WHERE { ?s ?p ?o }", 50)


def test_pipeline_happy_path(kg, linker):
    sparql = """```sparql
SELECT DISTINCT ?diseaseName WHERE {
  ?drug rdfs:label ?n ; :hasAssociation ?a .
  FILTER(LCASE(STR(?n)) = "metformin")
  ?a a :Indication ; :forDisease/rdfs:label ?diseaseName .
}
```"""
    llm = FakeLLM([sparql, "Metformin is indicated for type 2 diabetes ..."])
    out = KGQA(kg, llm, settings(), linker).ask("What is metformin indicated for?")
    assert out.ok and len(out.result) == 3
    assert len(out.attempts) == 1
    assert out.answer.startswith("Metformin")
    assert "res:drug_1725" in llm.calls[0][-1]["content"]


def test_pipeline_repairs_syntax_error(kg, linker):
    bad = "```sparql\nSELECT ?x WHERE { ?x rdfs:label }\n```"
    good = "```sparql\nSELECT ?name WHERE { ?d a :Drug ; rdfs:label ?name }\n```"
    llm = FakeLLM([bad, good, "Ten drugs."])
    out = KGQA(kg, llm, settings(), linker).ask("List all drugs")
    assert out.ok and len(out.result) == 10
    assert out.attempts[0].error and out.attempts[1].error is None
    assert "failed" in llm.calls[1][-1]["content"]


def test_pipeline_empty_result_retries_once(kg, linker):
    empty = "```sparql\nSELECT ?n WHERE { ?d rdfs:label ?n . FILTER(?n = \"nothing\") }\n```"
    llm = FakeLLM([empty, empty])
    out = KGQA(kg, llm, settings(), linker).ask("Unanswerable question")
    assert out.ok and len(out.result) == 0
    assert len(out.attempts) == 2
    assert out.answer == NO_RESULTS_ANSWER
