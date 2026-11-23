"""Knowledge-graph access layer with two interchangeable backends.

* ``GraphDBKG``  - talks to a GraphDB repository over the SPARQL 1.1 protocol.
* ``LocalKG``    - loads Turtle files into an in-memory rdflib graph.

Both return SELECT results in the same shape, so the rest of the app does not
care which one is active. ``get_kg()`` picks GraphDB when it is reachable and
falls back to the local files otherwise (``KG_BACKEND=auto``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import requests
from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import NamespaceManager

from .config import PREFIXES, Settings, get_settings

_COMMENT = re.compile(r"#[^\n]*")
_PREFIX_DECL = re.compile(r"(?is)^\s*(PREFIX\s+[\w-]*:\s*<[^>]*>|BASE\s*<[^>]*>)")
_IRI = re.compile(r"<[^>]*>")


def query_form(query: str) -> str:
    """Return SELECT / CONSTRUCT / DESCRIBE / ASK / UPDATE for a SPARQL string."""
    body = _IRI.sub("<>", query)
    body = _COMMENT.sub("", body)
    while True:
        m = _PREFIX_DECL.match(body)
        if not m:
            break
        body = body[m.end():]
    word = re.match(r"\s*(\w+)", body)
    keyword = word.group(1).upper() if word else ""
    if keyword in {"SELECT", "CONSTRUCT", "DESCRIBE", "ASK"}:
        return keyword
    if keyword in {"INSERT", "DELETE", "WITH", "LOAD", "CLEAR", "DROP", "CREATE", "ADD", "MOVE", "COPY"}:
        return "UPDATE"
    return keyword or "UNKNOWN"


def namespace_manager() -> NamespaceManager:
    nm = NamespaceManager(Graph(), bind_namespaces="none")
    for p, ns in PREFIXES.items():
        nm.bind(p, ns, override=True)
    return nm


_NM = namespace_manager()


def compact(term) -> str:
    """Human-readable form of an RDF term: prefixed names for IRIs, plain text for literals."""
    if term is None:
        return ""
    if isinstance(term, URIRef):
        try:
            return _NM.normalizeUri(term)
        except Exception:
            return str(term)
    if isinstance(term, BNode):
        return f"_:{term}"
    return str(term)


@dataclass
class SelectResult:
    variables: list[str]
    rows: list[dict]

    def as_text_rows(self) -> list[dict[str, str]]:
        return [{v: compact(r.get(v)) for v in self.variables} for r in self.rows]

    def __len__(self) -> int:
        return len(self.rows)


class KGError(RuntimeError):
    pass


class BaseKG:
    name = "base"

    def describe(self) -> str:
        raise NotImplementedError

    def select(self, query: str) -> SelectResult:
        raise NotImplementedError

    def graph_query(self, query: str) -> Graph:
        """Run a CONSTRUCT or DESCRIBE query and return the resulting graph."""
        raise NotImplementedError

    def ask(self, query: str) -> bool:
        raise NotImplementedError

    def update(self, query: str) -> None:
        raise NotImplementedError

    def triple_count(self) -> int:
        res = self.select("SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }")
        return int(res.rows[0]["n"]) if res.rows else 0

    def snapshot(self) -> Graph:
        """An in-memory copy of the whole KG (used to run updates safely)."""
        raise NotImplementedError

    def run(self, query: str):
        form = query_form(query)
        if form == "SELECT":
            return form, self.select(query)
        if form in {"CONSTRUCT", "DESCRIBE"}:
            return form, self.graph_query(query)
        if form == "ASK":
            return form, self.ask(query)
        if form == "UPDATE":
            self.update(query)
            return form, None
        raise KGError(f"Unsupported query form: {form or 'empty query'}")


def _bind_prefixes(g: Graph) -> Graph:
    for p, ns in PREFIXES.items():
        g.bind(p, ns, override=True)
    return g


class LocalKG(BaseKG):
    """In-memory rdflib graph loaded from Turtle files (no reasoning)."""

    name = "local"

    def __init__(self, files: list[Path] | None = None, graph: Graph | None = None):
        self.files = list(files or [])
        if graph is not None:
            self.graph = graph
        else:
            self.graph = Graph()
            for f in self.files:
                if not Path(f).exists():
                    raise KGError(f"KG file not found: {f}")
                self.graph.parse(str(f), format="turtle")
        _bind_prefixes(self.graph)

    def describe(self) -> str:
        names = ", ".join(Path(f).name for f in self.files) or "in-memory graph"
        return f"Local rdflib graph ({names})"

    def _query(self, query: str, consume):
        # rdflib evaluates lazily: errors can surface while reading the results,
        # and it raises plain Exception for some invalid queries (e.g. COUNT inside
        # FILTER). Parse, evaluate and read inside one guard.
        try:
            return consume(self.graph.query(query))
        except Exception as exc:
            raise KGError(f"{type(exc).__name__}: {exc}") from exc

    def select(self, query: str) -> SelectResult:
        def consume(res):
            rows = [{str(k): v for k, v in b.items() if v is not None} for b in res.bindings]
            return SelectResult([str(v) for v in res.vars], rows)

        return self._query(query, consume)

    def graph_query(self, query: str) -> Graph:
        return _bind_prefixes(self._query(query, lambda res: res.graph))

    def ask(self, query: str) -> bool:
        return self._query(query, lambda res: bool(res.askAnswer))

    def update(self, query: str) -> None:
        try:
            self.graph.update(query)
        except Exception as exc:
            raise KGError(str(exc)) from exc

    def triple_count(self) -> int:
        return len(self.graph)

    def snapshot(self) -> Graph:
        g = Graph()
        for t in self.graph:
            g.add(t)
        return _bind_prefixes(g)


class GraphDBKG(BaseKG):
    """GraphDB repository accessed through its SPARQL endpoint."""

    name = "graphdb"

    def __init__(self, base_url: str, repo: str, timeout: float = 60.0):
        self.base_url = base_url.rstrip("/")
        self.repo = repo
        self.endpoint = f"{self.base_url}/repositories/{repo}"
        self.timeout = timeout

    def describe(self) -> str:
        return f"GraphDB repository '{self.repo}' at {self.base_url}"

    def ping(self) -> bool:
        try:
            r = requests.get(f"{self.endpoint}/size", timeout=2)
            return r.ok
        except requests.RequestException:
            return False

    def _post(self, query: str, accept: str) -> requests.Response:
        try:
            r = requests.post(
                self.endpoint,
                data={"query": query},
                headers={"Accept": accept},
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise KGError(f"Cannot reach GraphDB at {self.endpoint}: {exc}") from exc
        if not r.ok:
            raise KGError(f"GraphDB error {r.status_code}: {r.text.strip()[:500]}")
        return r

    @staticmethod
    def _term(b: dict):
        t = b.get("type")
        if t == "uri":
            return URIRef(b["value"])
        if t == "bnode":
            return BNode(b["value"])
        return Literal(
            b["value"],
            lang=b.get("xml:lang"),
            datatype=URIRef(b["datatype"]) if b.get("datatype") else None,
        )

    def select(self, query: str) -> SelectResult:
        data = self._post(query, "application/sparql-results+json").json()
        variables = data["head"].get("vars", [])
        rows = [{k: self._term(v) for k, v in b.items()} for b in data["results"]["bindings"]]
        return SelectResult(variables, rows)

    def graph_query(self, query: str) -> Graph:
        r = self._post(query, "text/turtle")
        g = Graph()
        g.parse(data=r.text, format="turtle")
        return _bind_prefixes(g)

    def ask(self, query: str) -> bool:
        return bool(self._post(query, "application/sparql-results+json").json().get("boolean"))

    def update(self, query: str) -> None:
        try:
            r = requests.post(f"{self.endpoint}/statements", data={"update": query}, timeout=self.timeout)
        except requests.RequestException as exc:
            raise KGError(f"Cannot reach GraphDB at {self.endpoint}: {exc}") from exc
        if not r.ok:
            raise KGError(f"GraphDB update error {r.status_code}: {r.text.strip()[:500]}")

    def triple_count(self) -> int:
        try:
            r = requests.get(f"{self.endpoint}/size", timeout=self.timeout)
            if r.ok:
                return int(r.text.strip())
        except (requests.RequestException, ValueError):
            pass
        return super().triple_count()

    def snapshot(self) -> Graph:
        try:
            r = requests.get(
                f"{self.endpoint}/statements",
                params={"infer": "false"},
                headers={"Accept": "text/turtle"},
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise KGError(f"Cannot export GraphDB repository: {exc}") from exc
        if not r.ok:
            raise KGError(f"GraphDB export error {r.status_code}: {r.text[:300]}")
        g = Graph()
        g.parse(data=r.text, format="turtle")
        return _bind_prefixes(g)


def get_kg(settings: Settings | None = None) -> BaseKG:
    s = settings or get_settings()
    if s.kg_backend in {"graphdb", "auto"}:
        gdb = GraphDBKG(s.graphdb_url, s.graphdb_repo)
        if gdb.ping():
            return gdb
        if s.kg_backend == "graphdb":
            raise KGError(
                f"GraphDB repository '{s.graphdb_repo}' is not reachable at {s.graphdb_url}. "
                "Start GraphDB or set KG_BACKEND=local."
            )
    if s.kg_backend not in {"graphdb", "auto", "local"}:
        raise KGError(f"Unknown KG_BACKEND '{s.kg_backend}' (use auto, graphdb or local)")
    return LocalKG(s.kg_files)


def format_table(variables: list[str], rows: list[dict[str, str]], max_width: int = 70) -> str:
    """Plain-text table of SELECT rows (used in result files and LLM prompts)."""
    if not rows:
        return "(no results)"
    widths = {v: min(max(len(v), *(len(r.get(v, "")) for r in rows)), max_width) for v in variables}

    def cell(v: str, text: str) -> str:
        text = text if len(text) <= widths[v] else text[: widths[v] - 3] + "..."
        return text.ljust(widths[v])

    lines = [" | ".join(cell(v, v) for v in variables).rstrip()]
    lines.append("-+-".join("-" * widths[v] for v in variables))
    lines += [" | ".join(cell(v, r.get(v, "")) for v in variables).rstrip() for r in rows]
    return "\n".join(lines)
