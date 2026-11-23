"""Question answering pipeline: question -> entities -> SPARQL -> KG results -> answer.

1. Entity linking finds the drugs, diseases, etc. mentioned in the question.
2. The LLM writes a SPARQL SELECT query (schema + few-shot prompt).
3. The query is checked (read-only, parseable, prefixes added) and run on the KG.
4. On a syntax/runtime error, or no results, the error is fed back and the LLM
   retries (up to KGQA_MAX_ATTEMPTS attempts in total).
5. The LLM writes the final answer from the result rows only.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

from rdflib.plugins.sparql import prepareQuery

from .config import PREFIXES, Settings, get_settings
from .kg import BaseKG, KGError, SelectResult, format_table, query_form
from .linker import EntityLinker, Match
from .llm import OllamaClient
from .prompts import answer_messages, is_indonesian, is_yes_no, repair_message, sparql_messages

_CODE_BLOCK = re.compile(r"```(?:sparql|SPARQL|sql)?\s*\n?(.*?)```", re.S)
_QUERY_START = re.compile(r"(?is)\b(PREFIX|SELECT|ASK|CONSTRUCT|DESCRIBE|INSERT|DELETE)\b")

NO_RESULTS_ANSWER = "The knowledge graph has no information that matches this question."
NO_RESULTS_ANSWER_ID = "Knowledge graph tidak memiliki informasi yang sesuai dengan pertanyaan ini."
NO_RESULTS_ANSWERS = {NO_RESULTS_ANSWER, NO_RESULTS_ANSWER_ID}


@dataclass
class Attempt:
    sparql: str
    error: str | None = None
    rows: int | None = None


@dataclass
class QAResult:
    question: str
    entities: list[Match] = field(default_factory=list)
    attempts: list[Attempt] = field(default_factory=list)
    result: SelectResult | None = None
    answer: str = ""
    error: str | None = None
    timings: dict[str, float] = field(default_factory=dict)
    final_sparql: str = ""  # the query whose results were used for the answer

    @property
    def sparql(self) -> str:
        if self.final_sparql:
            return self.final_sparql
        return self.attempts[-1].sparql if self.attempts else ""

    @property
    def ok(self) -> bool:
        return self.error is None and self.result is not None


def extract_sparql(text: str) -> str:
    """Pull the SPARQL query out of an LLM reply."""
    m = _CODE_BLOCK.search(text)
    body = m.group(1) if m else text
    start = _QUERY_START.search(body)
    return body[start.start():].strip() if start else body.strip()


def add_missing_prefixes(query: str) -> str:
    missing = [
        f"PREFIX {p}: <{ns}>"
        for p, ns in PREFIXES.items()
        if not re.search(rf"(?i)PREFIX\s+{re.escape(p)}:", query)
    ]
    return ("\n".join(missing) + "\n" + query) if missing else query


_DATE_LITERAL = re.compile(r'"(\d{4}(?:-\d{2}){0,2})(?:T[\d:.Z+-]*)?"\s*\^\^\s*(?:xsd:|<http://www\.w3\.org/2001/XMLSchema#>?)(?:date|dateTime|gYear)\b')
_DATE_CAST = re.compile(r"(?i)\bxsd:(?:date|dateTime)\s*\(")
_YEAR_FN = re.compile(r"(?i)\bYEAR\s*\(\s*(\?\w+)\s*\)")


def normalize_dates(query: str) -> str:
    """:approvalDate values are plain "YYYY-MM-DD" strings, not xsd:date.

    Models routinely compare them with typed date literals or YEAR(), which
    silently returns no rows. Rewrite those to string operations, which sort
    correctly for ISO dates.
    """
    query = _DATE_LITERAL.sub(lambda m: f'"{m.group(1)}"', query)
    query = _DATE_CAST.sub("STR(", query)
    query = _YEAR_FN.sub(lambda m: f"xsd:integer(SUBSTR(STR({m.group(1)}), 1, 4))", query)
    return query


_BAD_PREFIXED = re.compile(r"(?<![\w?$]):(rdfs|rdf|owl|xsd):")
_AGG = re.compile(r"(?i)\b(COUNT|SUM|AVG|MIN|MAX|GROUP_CONCAT|SAMPLE)\s*\(")


_TYPED_STRING = re.compile(r'("(?:[^"\\]|\\.)*")\s*\^\^\s*(?:xsd:string|<http://www\.w3\.org/2001/XMLSchema#string>)')
_SELF_LABEL = re.compile(r"(\?\w+)(\s+rdfs:label\s+)\1\b")


def fix_literal_and_label_slips(query: str) -> str:
    """Two slips seen in model output:
    * `"x"^^xsd:string` - the same value as `"x"` in RDF 1.1, but rdflib compares
      LCASE(STR(?l)) with it as unequal, so filters silently fail;
    * `?disease rdfs:label ?disease` - subject and object are the same variable, which
      can never match; the label variable is renamed to ?diseaseName.
    """
    query = _TYPED_STRING.sub(lambda m: m.group(1), query)
    return _SELF_LABEL.sub(lambda m: f"{m.group(1)}{m.group(2)}{m.group(1)}Name", query)


def fix_double_prefixes(query: str) -> str:
    """`:rdfs:label` (copied from hints) is a legal but non-existent IRI; make it `rdfs:label`."""
    return _BAD_PREFIXED.sub(lambda m: f"{m.group(1)}:", query)


def _balanced(text: str, open_idx: int) -> int:
    """Index just past the parenthesis group that opens at text[open_idx]."""
    depth = 0
    for i in range(open_idx, len(text)):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return i + 1
    return -1


def move_aggregate_filters(query: str) -> str:
    """Aggregates are not allowed in FILTER. Move such conditions into HAVING
    (adding GROUP BY on the projected variables when there is none)."""
    moved: list[str] = []
    out, pos = [], 0
    for m in re.finditer(r"(?i)\bFILTER\s*\(", query):
        if m.start() < pos:
            continue
        end = _balanced(query, m.end() - 1)
        if end < 0:
            break
        inner = query[m.end():end - 1]
        if _AGG.search(inner):
            out.append(query[pos:m.start()])
            moved.append(inner.strip())
            pos = end
    if not moved:
        return query
    out.append(query[pos:])
    query = "".join(out)
    if re.search(r"(?i)\bHAVING\b", query):
        return query
    having = "HAVING (" + " && ".join(f"({e})" for e in moved) + ")"
    close = query.rfind("}")
    head, tail = query[: close + 1], query[close + 1:]
    group = re.search(r"(?i)\bGROUP\s+BY\b[^\n]*", tail)
    if group:
        tail = tail[: group.end()] + f"\n{having}" + tail[group.end():]
    else:
        select = re.search(r"(?is)\bSELECT\s+(?:DISTINCT\s+|REDUCED\s+)?(.*?)\bWHERE\b|\bSELECT\s+(?:DISTINCT\s+)?(.*?)\{", head)
        clause = (select.group(1) or select.group(2) or "") if select else ""
        clause = re.sub(r"\([^()]*(?:\([^()]*\)[^()]*)*\)", " ", clause)
        variables = re.findall(r"\?\w+", clause)
        if not variables:
            return query
        tail = f"\nGROUP BY {' '.join(dict.fromkeys(variables))}\n{having}" + tail
    return head + tail


_LABEL_LITERAL = re.compile(r'rdfs:label\s+"((?:[^"\\]|\\.)*)"(?:@[A-Za-z-]+|\^\^xsd:string)?')


def relax_label_literals(query: str) -> str:
    """`?x rdfs:label "GABA receptor activation"` only matches an exact, untagged
    literal, but labels are tagged @en and the model's capitalisation varies.
    Replace each literal label object with a variable plus a case-insensitive
    FILTER placed at the end of the same group."""
    count = 0
    while True:
        m = _LABEL_LITERAL.search(query)
        if not m:
            return query
        count += 1
        var = f"?_label{count}"
        value = m.group(1).lower().replace('"', '\\"')
        query = query[: m.start()] + f"rdfs:label {var}" + query[m.end():]
        # Find the '}' that closes the group containing the pattern.
        depth, i = 0, m.start()
        while i < len(query):
            c = query[i]
            if c == "{":
                depth += 1
            elif c == "}":
                if depth == 0:
                    break
                depth -= 1
            i += 1
        query = query[:i] + f'\n  FILTER(LCASE(STR({var})) = "{value}")\n' + query[i:]


def _where_body(query: str) -> tuple[str, str]:
    """(projection clause, WHERE group) of a SELECT query; empty strings if not found."""
    m = re.search(r"(?is)\bSELECT\b(.*?)(?:\bWHERE\b\s*)?\{", query)
    if not m:
        return "", ""
    start = m.end() - 1
    depth = 0
    for i in range(start, len(query)):
        if query[i] == "{":
            depth += 1
        elif query[i] == "}":
            depth -= 1
            if depth == 0:
                return m.group(1), query[start:i + 1]
    return m.group(1), query[start:]


def _projection_vars(projection: str) -> tuple[set[str], set[str]]:
    """(variables used in the projection, variables the projection defines with AS)."""
    defined = set(re.findall(r"(?i)\bAS\s+\?(\w+)", projection))
    used = set(re.findall(r"\?(\w+)", projection)) - defined
    return used, defined


def _rename_candidate(var: str, bound: set[str]) -> str | None:
    """A bound variable the model most likely meant: ?contra -> ?contraAssoc, ?approvalDate -> ?date.

    Prefers a bound name that starts with the unbound one (a label, ending in "Name", first,
    then the shortest); otherwise a bound name of 3+ characters that the unbound one ends with.
    """
    low = var.lower()
    longer = [b for b in bound if b.lower().startswith(low) and b != var]
    if longer:
        named = [b for b in longer if b.endswith("Name")]
        return min(named or longer, key=len)
    shorter = [b for b in bound if len(b) >= 3 and low.endswith(b.lower()) and b != var]
    if len(shorter) == 1:
        return shorter[0]
    return None


def repair_unbound_variables(query: str) -> str:
    """Fix SELECT queries that project or aggregate variables the WHERE clause never binds.

    Small models often bind ?contraAssoc but select ?contra, or bind ?date but select
    ?approvalDate, so the column is empty and COUNT is 0. Rename such variables to the obvious
    bound one; drop plain projected variables that have no match (when other columns remain).
    Raises ValueError, listing the bound variables, if something is still unbound.
    """
    projection, where = _where_body(query)
    if not where or "*" in projection:
        return query
    bound = set(re.findall(r"\?(\w+)", where))
    used, defined = _projection_vars(projection)
    missing = sorted(v for v in used if v not in bound)
    for var in missing:
        target = _rename_candidate(var, bound)
        if target:
            query = re.sub(rf"\?{re.escape(var)}\b", f"?{target}", query)

    projection, where = _where_body(query)
    used, defined = _projection_vars(projection)
    missing = [v for v in used if v not in bound]
    plain = re.sub(r"\([^()]*(?:\([^()]*\)[^()]*)*\)", " ", projection)  # outside (expr AS ?x)
    droppable = [v for v in missing if re.search(rf"\?{re.escape(v)}\b", plain)]
    remaining = [v for v in re.findall(r"\?(\w+)", plain) if v not in droppable]
    if droppable and (remaining or defined):
        new_projection = projection
        for v in droppable:
            new_projection = re.sub(rf"\s*\?{re.escape(v)}\b(?![^()]*\))", "", new_projection)
        query = query.replace(projection, new_projection, 1)
        missing = [v for v in missing if v not in droppable]

    if missing:
        names = ", ".join(f"?{v}" for v in sorted(missing))
        known = ", ".join(f"?{v}" for v in sorted(bound))
        raise ValueError(
            f"variable(s) {names} used in SELECT are never bound in the WHERE clause, so they would be empty "
            f"(and COUNT would be 0). The WHERE clause binds: {known}. Use one of those instead."
        )
    return query


def explain_error(message: str) -> str:
    """Turn engine errors a small model cannot act on into a concrete hint."""
    if "Aggregate_" in message or "aggregate" in message.lower():
        return ("aggregates such as COUNT/MAX cannot be used inside FILTER or WHERE. "
                "Use GROUP BY ... HAVING (COUNT(DISTINCT ?x) >= n), or compute them in SELECT.")
    if "Unknown namespace prefix" in message:
        return f"{message}. Use only the prefixes :, res:, rdf:, rdfs:, owl: and xsd:."
    return message


def prepare_query(raw: str, max_rows: int) -> str:
    """Validate and normalise a generated query. Raises ValueError on problems."""
    query = normalize_dates(fix_literal_and_label_slips(fix_double_prefixes(raw.strip())))
    query = relax_label_literals(move_aggregate_filters(query))
    query = add_missing_prefixes(query)
    form = query_form(query)
    if form not in {"SELECT", "ASK"}:
        raise ValueError(f"Only read-only SELECT/ASK queries are allowed, got {form}.")
    try:
        prepareQuery(query)
    except Exception as exc:
        raise ValueError(f"SPARQL syntax error: {exc}") from exc
    if form == "SELECT":
        query = repair_unbound_variables(query)
    if form == "SELECT" and not re.search(r"(?i)\bLIMIT\s+\d+", query):
        query += f"\nLIMIT {max_rows * 4}"
    return query


def _words(name: str) -> str:
    """camelCase column name -> plain words: maxLLR -> max LLR, approvalDate -> approval date."""
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name).replace("_", " ").lower().replace("llr", "LLR")


def render_rows(variables: list[str], rows: list[dict[str, str]], max_rows: int) -> str:
    """Bullet list of result rows: the first name-like value, then the other columns labelled.

    IRI columns (res:..., :...) are left out when the row has readable values.
    """
    lines = []
    for row in rows[:max_rows]:
        cells = [(v, row.get(v, "")) for v in variables if row.get(v, "")]
        readable = [(v, x) for v, x in cells if not re.match(r"^(res:|:|https?://)", x)] or cells
        if not readable:
            continue
        head, rest = readable[0][1], readable[1:]
        extra = ", ".join(f"{_words(v)}: {x}" for v, x in rest)
        lines.append(f"- {head}" + (f" ({extra})" if extra else ""))
    if len(rows) > max_rows:
        lines.append(f"- ... {len(rows) - max_rows} more")
    return "\n".join(lines)


def lead_sentence(text: str) -> str:
    """The model's introduction only: first line, cut after the first colon (models tend to keep
    listing, and translating, the items after it); a colon is added when missing."""
    line = text.strip().split("\n")[0].strip().lstrip("-* ").strip()
    if ":" in line:
        return line[: line.index(":") + 1]
    line = re.split(r"(?<=[.!?])\s", line)[0].rstrip(" .")
    return f"{line}:"


class KGQA:
    def __init__(self, kg: BaseKG, llm: OllamaClient, settings: Settings | None = None,
                 linker: EntityLinker | None = None):
        self.kg = kg
        self.llm = llm
        self.settings = settings or get_settings()
        self.linker = linker or EntityLinker(kg)

    def _execute(self, query: str) -> SelectResult:
        form = query_form(query)
        if form == "ASK":
            value = self.kg.ask(query)
            from rdflib import Literal

            return SelectResult(["answer"], [{"answer": Literal("yes" if value else "no")}])
        return self.kg.select(query)

    def ask(self, question: str) -> QAResult:
        out = QAResult(question=question)
        t0 = time.perf_counter()
        out.entities = self.linker.link(question)
        out.timings["linking"] = time.perf_counter() - t0

        messages = sparql_messages(question, [m.hint() for m in out.entities])
        retried_empty = False
        t_gen = t_run = 0.0
        for _ in range(max(1, self.settings.max_attempts)):
            t = time.perf_counter()
            try:
                reply = self.llm.chat(messages)
            except Exception as exc:
                out.error = str(exc)
                break
            t_gen += time.perf_counter() - t
            raw = extract_sparql(reply)
            attempt = Attempt(sparql=raw)
            out.attempts.append(attempt)
            messages.append({"role": "assistant", "content": reply})

            try:
                query = prepare_query(raw, self.settings.max_rows)
                attempt.sparql = query
                t = time.perf_counter()
                result = self._execute(query)
                t_run += time.perf_counter() - t
            except (ValueError, KGError) as exc:
                attempt.error = str(exc)
                messages.append(repair_message(f"That query failed: {explain_error(str(exc))}"))
                continue

            attempt.rows = len(result)
            unbound = [v for v in result.variables if result.rows and all(v not in r for r in result.rows)]
            if unbound:
                names = ", ".join(f"?{v}" for v in unbound)
                attempt.error = f"result column(s) {names} are never bound"
                messages.append(repair_message(
                    f"That query returned rows, but {names} is never bound in the WHERE clause. "
                    f"Add the triple pattern that binds it, e.g. ?drug rdfs:label ?drugName ."))
                continue
            out.result = result
            out.final_sparql = query
            if len(result) == 0 and not retried_empty:
                # One retry for empty results: often a wrong path or an exact-label typo.
                retried_empty = True
                messages.append(repair_message("That query ran but returned no results."))
                continue
            break
        out.timings["sparql_generation"] = t_gen
        out.timings["query_execution"] = t_run

        if out.result is None:
            if not out.error:
                last = out.attempts[-1].error if out.attempts else "no query was generated"
                out.error = (f"Could not build a working SPARQL query after {len(out.attempts)} "
                             f"attempt(s). Last problem: {last}")
            out.timings["total"] = time.perf_counter() - t0
            return out

        t = time.perf_counter()
        if len(out.result) == 0:
            out.answer = NO_RESULTS_ANSWER_ID if is_indonesian(question) else NO_RESULTS_ANSWER
        else:
            rows = out.result.as_text_rows()
            shown = rows[: self.settings.max_rows]
            table = format_table(out.result.variables, shown, max_width=120)
            form = query_form(out.sparql)
            yes_no = is_yes_no(question, form)
            try:
                text = self.llm.chat(
                    answer_messages(question, out.sparql, table, truncated=len(rows) > len(shown),
                                    form=form, n_rows=len(rows)),
                    temperature=0.1,
                    max_tokens=200 if not yes_no else 300,
                ).strip()
                if yes_no:
                    out.answer = text
                else:
                    out.answer = f"{lead_sentence(text)}\n\n{render_rows(out.result.variables, rows, self.settings.max_rows)}"
            except Exception as exc:
                out.error = str(exc)
        out.timings["answer_generation"] = time.perf_counter() - t
        out.timings["total"] = time.perf_counter() - t0
        return out
