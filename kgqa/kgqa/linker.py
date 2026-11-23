"""Lightweight entity linking: find KG entities mentioned in a question.

Small local LLMs often misspell or paraphrase entity names, which makes the
exact-label filters in generated SPARQL return nothing. Before generating the
query we look up which drugs, diseases, adverse events, targets, pathways and
agencies the question mentions (exact or fuzzy match on rdfs:label) and give
the LLM their exact labels and IRIs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from .config import prefix_block
from .kg import BaseKG, compact

LINKABLE_CLASSES = ["Drug", "Disease", "AdverseEvent", "Target", "Protein", "Pathway", "RegulatoryAgency"]

_TOKEN = re.compile(r"[a-z0-9]+")

PARTIAL_SCORE = 0.8
# Entity labels that collide with schema vocabulary: linking them misleads the
# model (e.g. the MedDRA event "Off label use" vs the class :OffLabelUse).
SCHEMA_TERMS = {"off label use"}
STOPWORDS = {
    "a", "an", "the", "of", "in", "on", "for", "to", "by", "and", "or", "with", "is", "are", "was",
    "what", "which", "who", "how", "does", "do", "drug", "drugs", "disease", "diseases", "used",
}


def _norm(text: str) -> str:
    return " ".join(_TOKEN.findall(text.lower()))


@dataclass
class Entity:
    iri: str
    label: str
    cls: str
    norm: str


@dataclass
class Match:
    entity: Entity
    score: float
    mention: str

    def hint(self) -> str:
        quality = "" if self.score >= 1.0 else "  (possible match, ignore if irrelevant)"
        return f'{compact_iri(self.entity.iri)} = {self.entity.cls} named "{self.entity.label}"{quality}'


def compact_iri(iri: str) -> str:
    from rdflib import URIRef

    return compact(URIRef(iri))


class EntityLinker:
    def __init__(self, kg: BaseKG, min_score: float = 0.88):
        self.min_score = min_score
        self.entities: list[Entity] = []
        values = " ".join(f":{c}" for c in LINKABLE_CLASSES)
        query = prefix_block() + f"""
SELECT DISTINCT ?s ?label ?cls WHERE {{
  VALUES ?cls {{ {values} }}
  ?s a ?cls ; rdfs:label ?label .
}}"""
        for row in kg.select(query).rows:
            label = str(row["label"])
            cls = compact(row["cls"]).lstrip(":")
            if cls == "Protein":
                label = label.split(" (")[0]  # UniProt names carry long synonym lists
            norm = _norm(label)
            if norm and norm not in SCHEMA_TERMS:
                self.entities.append(Entity(str(row["s"]), label, cls, norm))

    def __len__(self) -> int:
        return len(self.entities)

    @staticmethod
    def _partial(ent: Entity, grams: dict[int, set[str]], q_tokens: set[str]) -> str | None:
        """Weaker match for partial names.

        * the question covers >= 75% of a multi-word label's words, in any order
          ("type 2 diabetes" -> "Diabetes mellitus type 2"), or
        * a 2+ word phrase of the question appears inside the label
          ("gaba a receptor" -> "GABA-A receptor alpha-1/beta-2/gamma-2").
        """
        words = ent.norm.split()
        content = [w for w in words if w not in STOPWORDS]
        if len(content) >= 2:
            hit = [w for w in content if w in q_tokens]
            if len(hit) >= 2 and len(hit) / len(content) >= 0.75:
                return " ".join(hit)
        padded = f" {ent.norm} "
        for n in range(len(words) - 1, 1, -1):
            for g in grams.get(n, ()):
                parts = g.split()
                if parts[0] in STOPWORDS or parts[-1] in STOPWORDS or len(g) < 8:
                    continue
                if f" {g} " in padded:
                    return g
        return None

    def link(self, question: str, limit: int = 8) -> list[Match]:
        q = _norm(question)
        tokens = q.split()
        padded = f" {q} "
        best: dict[str, Match] = {}

        # n-grams of the question, for fuzzy matching (handles typos such as "metfromin").
        grams: dict[int, set[str]] = {}
        for n in range(1, 7):
            grams[n] = {" ".join(tokens[i:i + n]) for i in range(len(tokens) - n + 1)}

        q_tokens = set(tokens)
        for ent in self.entities:
            if f" {ent.norm} " in padded:
                score, mention = 1.0, ent.norm
            elif (partial := self._partial(ent, grams, q_tokens)) is not None:
                score, mention = PARTIAL_SCORE, partial
            else:
                k = len(ent.norm.split())
                score, mention = 0.0, ""
                if k == 1 and len(ent.norm) < 5:
                    continue  # short single words (e.g. "fda") only match exactly
                for n in {k - 1, k, k + 1}:
                    for g in grams.get(n, ()):
                        if abs(len(g) - len(ent.norm)) > max(3, len(ent.norm) // 4):
                            continue
                        r = SequenceMatcher(None, g, ent.norm).ratio()
                        if r > score:
                            score, mention = r, g
                if score < self.min_score:
                    continue
            prev = best.get(ent.iri)
            if prev is None or score > prev.score:
                best[ent.iri] = Match(ent, score, mention)

        matches = sorted(best.values(), key=lambda m: (-m.score, -len(m.mention), m.entity.label))
        # Drop matches whose mention is fully covered by a longer, better mention
        # (e.g. "diabetes mellitus" when "diabetes mellitus type 2" matched).
        kept: list[Match] = []
        for m in matches:
            if any(m.mention != k.mention and f" {m.mention} " in f" {k.mention} " and k.score >= m.score
                   for k in kept):
                continue
            kept.append(m)
        return kept[:limit]
