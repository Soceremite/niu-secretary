from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, Sequence

from airesearch.research_digest import FACT_TYPE_ORDER, DigestFact, DigestPaper, build_research_digest


CLUSTER_THRESHOLD = 0.22
SEMANTIC_CLUSTER_THRESHOLD = 0.82
STOPWORDS = {
    "about",
    "across",
    "after",
    "against",
    "also",
    "among",
    "and",
    "are",
    "based",
    "been",
    "being",
    "between",
    "both",
    "can",
    "from",
    "for",
    "has",
    "have",
    "into",
    "its",
    "may",
    "method",
    "model",
    "models",
    "not",
    "only",
    "our",
    "paper",
    "present",
    "presented",
    "propose",
    "proposes",
    "show",
    "shows",
    "that",
    "the",
    "their",
    "this",
    "through",
    "using",
    "uses",
    "was",
    "were",
    "with",
}


@dataclass(frozen=True)
class ClusterFactRef:
    paper_key: str
    paper_title: str
    year: int | None
    fact_name: str
    statement: str
    confidence: float
    evidence_source_path: str | None


@dataclass(frozen=True)
class ResearchCluster:
    cluster_id: str
    fact_type: str
    label: str
    token_signature: list[str]
    facts: list[ClusterFactRef]

    @property
    def paper_count(self) -> int:
        return len({fact.paper_key for fact in self.facts})

    @property
    def fact_count(self) -> int:
        return len(self.facts)

    @property
    def average_confidence(self) -> float:
        if not self.facts:
            return 0.0
        return sum(fact.confidence for fact in self.facts) / len(self.facts)


@dataclass(frozen=True)
class SingletonSummary:
    fact_type: str
    fact_count: int
    paper_count: int


@dataclass(frozen=True)
class ResearchClusters:
    generated_at: str
    paper_count: int
    fact_count: int
    mode: str
    semantic_threshold: float | None
    clusters: list[ResearchCluster]
    singleton_summaries: list[SingletonSummary]

    @property
    def cluster_count(self) -> int:
        return len(self.clusters)

    @property
    def clustered_fact_count(self) -> int:
        return sum(cluster.fact_count for cluster in self.clusters)

    @property
    def singleton_count(self) -> int:
        return sum(summary.fact_count for summary in self.singleton_summaries)


@dataclass
class _ClusterDraft:
    fact_type: str
    facts: list[ClusterFactRef]
    token_counter: Counter[str]
    token_union: set[str]


class EmbeddingProvider(Protocol):
    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        """Return one embedding vector for each input text."""


class SemanticClusteringError(RuntimeError):
    pass


@dataclass
class _SemanticFactItem:
    fact_type: str
    ref: ClusterFactRef
    tokens: set[str]
    vector: list[float]


@dataclass
class _SemanticClusterDraft:
    fact_type: str
    facts: list[ClusterFactRef]
    token_counter: Counter[str]
    token_union: set[str]
    vectors: list[list[float]]

    @property
    def centroid(self) -> list[float]:
        if not self.vectors:
            return []
        width = min(len(vector) for vector in self.vectors)
        if width == 0:
            return []
        return [sum(vector[index] for vector in self.vectors) / len(self.vectors) for index in range(width)]


def _fact_type_title(fact_type: str) -> str:
    return fact_type.replace("_", " ").title()


def _tokenize(value: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9]+", value.lower())
    return {token for token in tokens if len(token) >= 3 and token not in STOPWORDS}


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    width = min(len(left), len(right))
    if width == 0:
        return 0.0
    dot = sum(left[index] * right[index] for index in range(width))
    left_norm = math.sqrt(sum(left[index] * left[index] for index in range(width)))
    right_norm = math.sqrt(sum(right[index] * right[index] for index in range(width)))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


def _fact_sort_key(item: tuple[str, DigestPaper, DigestFact]) -> tuple[str, float, str, str, str, str]:
    fact_type, paper, fact = item
    return (
        fact_type,
        -fact.confidence,
        paper.title.lower(),
        paper.paper_key,
        fact.name.lower(),
        fact.statement.lower(),
    )


def _cluster_sort_key(cluster: ResearchCluster) -> tuple[int, int, int, float, str]:
    fact_type_rank = FACT_TYPE_ORDER.index(cluster.fact_type) if cluster.fact_type in FACT_TYPE_ORDER else len(FACT_TYPE_ORDER)
    return (
        fact_type_rank,
        -cluster.paper_count,
        -cluster.fact_count,
        -cluster.average_confidence,
        cluster.label.lower(),
    )


def _token_signature(counter: Counter[str]) -> list[str]:
    return [token for token, _count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))[:5]]


def _label_from_signature(signature: list[str]) -> str:
    if not signature:
        return "Unlabeled Cluster"
    return " ".join(token.title() for token in signature[:4])


def _cluster_id(fact_type: str, signature: list[str], index: int) -> str:
    if signature:
        slug = "-".join(signature[:4])
    else:
        slug = f"cluster-{index + 1}"
    return f"{fact_type}:{slug}"


def _cluster_facts(items: list[tuple[str, DigestPaper, DigestFact]]) -> tuple[list[ResearchCluster], list[SingletonSummary]]:
    drafts_by_type: dict[str, list[_ClusterDraft]] = {}

    for fact_type, paper, fact in sorted(items, key=_fact_sort_key):
        tokens = _tokenize(f"{fact.name} {fact.statement}")
        ref = ClusterFactRef(
            paper_key=paper.paper_key,
            paper_title=paper.title,
            year=paper.year,
            fact_name=fact.name,
            statement=fact.statement,
            confidence=fact.confidence,
            evidence_source_path=fact.evidence_source_path,
        )
        drafts = drafts_by_type.setdefault(fact_type, [])
        best_index = -1
        best_score = 0.0
        for index, draft in enumerate(drafts):
            score = _jaccard(tokens, draft.token_union)
            if score > best_score:
                best_index = index
                best_score = score
        if best_index >= 0 and best_score >= CLUSTER_THRESHOLD:
            draft = drafts[best_index]
            draft.facts.append(ref)
            draft.token_counter.update(tokens)
            draft.token_union.update(tokens)
        else:
            drafts.append(
                _ClusterDraft(
                    fact_type=fact_type,
                    facts=[ref],
                    token_counter=Counter(tokens),
                    token_union=set(tokens),
                )
            )

    clusters: list[ResearchCluster] = []
    singleton_totals: dict[str, dict[str, Any]] = {}
    for fact_type, drafts in drafts_by_type.items():
        for draft in drafts:
            paper_keys = {fact.paper_key for fact in draft.facts}
            if len(draft.facts) >= 2 or len(paper_keys) >= 2:
                signature = _token_signature(draft.token_counter)
                clusters.append(
                    ResearchCluster(
                        cluster_id=_cluster_id(fact_type, signature, len(clusters)),
                        fact_type=fact_type,
                        label=_label_from_signature(signature),
                        token_signature=signature,
                        facts=sorted(
                            draft.facts,
                            key=lambda fact: (-fact.confidence, fact.paper_title.lower(), fact.paper_key, fact.statement),
                        ),
                    )
                )
            else:
                summary = singleton_totals.setdefault(fact_type, {"fact_count": 0, "paper_keys": set()})
                summary["fact_count"] += len(draft.facts)
                summary["paper_keys"].update(paper_keys)

    singleton_summaries = [
        SingletonSummary(fact_type=fact_type, fact_count=payload["fact_count"], paper_count=len(payload["paper_keys"]))
        for fact_type, payload in singleton_totals.items()
        if payload["fact_count"]
    ]
    singleton_summaries.sort(
        key=lambda summary: (
            FACT_TYPE_ORDER.index(summary.fact_type)
            if summary.fact_type in FACT_TYPE_ORDER
            else len(FACT_TYPE_ORDER),
            summary.fact_type,
        )
    )
    return sorted(clusters, key=_cluster_sort_key), singleton_summaries


def _summarize_singletons(singleton_totals: dict[str, dict[str, Any]]) -> list[SingletonSummary]:
    singleton_summaries = [
        SingletonSummary(fact_type=fact_type, fact_count=payload["fact_count"], paper_count=len(payload["paper_keys"]))
        for fact_type, payload in singleton_totals.items()
        if payload["fact_count"]
    ]
    singleton_summaries.sort(
        key=lambda summary: (
            FACT_TYPE_ORDER.index(summary.fact_type)
            if summary.fact_type in FACT_TYPE_ORDER
            else len(FACT_TYPE_ORDER),
            summary.fact_type,
        )
    )
    return singleton_summaries


def _cluster_facts_semantic(
    items: list[tuple[str, DigestPaper, DigestFact]],
    *,
    embedding_provider: EmbeddingProvider,
    threshold: float,
) -> tuple[list[ResearchCluster], list[SingletonSummary]]:
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("semantic_threshold must be between 0.0 and 1.0")
    if not items:
        return [], []

    sorted_items = sorted(items, key=_fact_sort_key)
    texts = [f"{fact.name}\n{fact.statement}" for _fact_type, _paper, fact in sorted_items]
    embeddings = embedding_provider.embed_texts(texts)
    return cluster_facts_semantic_from_embeddings(sorted_items, embeddings, threshold=threshold)


def cluster_facts_semantic_from_embeddings(
    sorted_items: list[tuple[str, DigestPaper, DigestFact]],
    embeddings: Sequence[Sequence[float]],
    *,
    threshold: float,
) -> tuple[list[ResearchCluster], list[SingletonSummary]]:
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("semantic_threshold must be between 0.0 and 1.0")
    if len(embeddings) != len(sorted_items):
        raise SemanticClusteringError(
            f"embedding provider returned {len(embeddings)} embeddings for {len(sorted_items)} texts"
        )

    drafts_by_type: dict[str, list[_SemanticClusterDraft]] = {}
    for (fact_type, paper, fact), vector in zip(sorted_items, embeddings):
        tokens = _tokenize(f"{fact.name} {fact.statement}")
        ref = ClusterFactRef(
            paper_key=paper.paper_key,
            paper_title=paper.title,
            year=paper.year,
            fact_name=fact.name,
            statement=fact.statement,
            confidence=fact.confidence,
            evidence_source_path=fact.evidence_source_path,
        )
        drafts = drafts_by_type.setdefault(fact_type, [])
        best_index = -1
        best_score = 0.0
        for index, draft in enumerate(drafts):
            score = _cosine_similarity(vector, draft.centroid)
            if score > best_score:
                best_index = index
                best_score = score
        if best_index >= 0 and best_score >= threshold:
            draft = drafts[best_index]
            draft.facts.append(ref)
            draft.token_counter.update(tokens)
            draft.token_union.update(tokens)
            draft.vectors.append(list(vector))
        else:
            drafts.append(
                _SemanticClusterDraft(
                    fact_type=fact_type,
                    facts=[ref],
                    token_counter=Counter(tokens),
                    token_union=set(tokens),
                    vectors=[list(vector)],
                )
            )

    clusters: list[ResearchCluster] = []
    singleton_totals: dict[str, dict[str, Any]] = {}
    for fact_type, drafts in drafts_by_type.items():
        for draft in drafts:
            paper_keys = {fact.paper_key for fact in draft.facts}
            if len(draft.facts) >= 2 or len(paper_keys) >= 2:
                signature = _token_signature(draft.token_counter)
                clusters.append(
                    ResearchCluster(
                        cluster_id=_cluster_id(fact_type, signature, len(clusters)),
                        fact_type=fact_type,
                        label=_label_from_signature(signature),
                        token_signature=signature,
                        facts=sorted(
                            draft.facts,
                            key=lambda fact: (-fact.confidence, fact.paper_title.lower(), fact.paper_key, fact.statement),
                        ),
                    )
                )
            else:
                summary = singleton_totals.setdefault(fact_type, {"fact_count": 0, "paper_keys": set()})
                summary["fact_count"] += len(draft.facts)
                summary["paper_keys"].update(paper_keys)

    return sorted(clusters, key=_cluster_sort_key), _summarize_singletons(singleton_totals)


def build_research_clusters(
    db_path: Path,
    *,
    mode: str = "token",
    embedding_provider: EmbeddingProvider | None = None,
    semantic_threshold: float = SEMANTIC_CLUSTER_THRESHOLD,
) -> ResearchClusters:
    if mode not in {"token", "semantic"}:
        raise ValueError(f"unsupported research cluster mode: {mode}")
    if mode == "semantic" and embedding_provider is None:
        raise SemanticClusteringError("semantic clustering requires an embedding provider")

    digest = build_research_digest(db_path)
    items: list[tuple[str, DigestPaper, DigestFact]] = []
    for paper in digest.papers:
        for fact_type, facts in paper.facts.items():
            for fact in facts:
                items.append((fact_type, paper, fact))
    if mode == "semantic":
        assert embedding_provider is not None
        clusters, singleton_summaries = _cluster_facts_semantic(
            items,
            embedding_provider=embedding_provider,
            threshold=semantic_threshold,
        )
        threshold_value: float | None = semantic_threshold
    else:
        clusters, singleton_summaries = _cluster_facts(items)
        threshold_value = None
    return ResearchClusters(
        generated_at=digest.generated_at,
        paper_count=digest.paper_count,
        fact_count=digest.fact_count,
        mode=mode,
        semantic_threshold=threshold_value,
        clusters=clusters,
        singleton_summaries=singleton_summaries,
    )


def render_markdown(report: ResearchClusters) -> str:
    lines = [
        "# AIResearch Research Clusters",
        "",
        f"Generated: {report.generated_at}",
        f"Papers: {report.paper_count}",
        f"Facts: {report.fact_count}",
        f"Mode: {report.mode}",
        f"Clusters: {report.cluster_count}",
        f"Clustered facts: {report.clustered_fact_count}",
        f"Singletons: {report.singleton_count}",
        "",
        "## Cluster Summary By Fact Type",
        "",
    ]
    if report.semantic_threshold is not None:
        lines.insert(6, f"Semantic threshold: {report.semantic_threshold:.2f}")
    cluster_counts = Counter(cluster.fact_type for cluster in report.clusters)
    for fact_type in FACT_TYPE_ORDER:
        if cluster_counts.get(fact_type) or any(summary.fact_type == fact_type for summary in report.singleton_summaries):
            singleton_count = next(
                (summary.fact_count for summary in report.singleton_summaries if summary.fact_type == fact_type),
                0,
            )
            lines.append(
                f"- {_fact_type_title(fact_type)}: clusters={cluster_counts.get(fact_type, 0)}, singletons={singleton_count}"
            )
    lines.extend(["", "## Fact Clusters", ""])
    if not report.clusters:
        lines.extend(["No multi-fact clusters found.", ""])
    for cluster in report.clusters:
        lines.extend(
            [
                f"### {cluster.label}",
                "",
                f"`{cluster.cluster_id}` | {_fact_type_title(cluster.fact_type)}",
                (
                    f"Papers: {cluster.paper_count} | Facts: {cluster.fact_count} | "
                    f"Average confidence: {cluster.average_confidence:.2f}"
                ),
                "Tokens: " + ", ".join(cluster.token_signature),
                "",
            ]
        )
        for fact in cluster.facts:
            title = fact.paper_title
            if fact.year:
                title += f" | {fact.year}"
            lines.append(f"- `{fact.paper_key}` {title}: {fact.fact_name} - {fact.statement} (confidence: {fact.confidence:.2f})")
            if fact.evidence_source_path:
                lines.append(f"  Evidence source: {fact.evidence_source_path}")
        lines.append("")
    lines.extend(["## Singleton Summary", ""])
    if not report.singleton_summaries:
        lines.append("No singleton facts.")
    for summary in report.singleton_summaries:
        lines.append(
            f"- {_fact_type_title(summary.fact_type)}: {summary.fact_count} facts across {summary.paper_count} papers"
        )
    return "\n".join(lines).rstrip() + "\n"


def research_clusters_to_dict(report: ResearchClusters) -> dict[str, Any]:
    return {
        "generated_at": report.generated_at,
        "paper_count": report.paper_count,
        "fact_count": report.fact_count,
        "mode": report.mode,
        "semantic_threshold": report.semantic_threshold,
        "cluster_count": report.cluster_count,
        "clustered_fact_count": report.clustered_fact_count,
        "singleton_count": report.singleton_count,
        "clusters": [
            {
                "cluster_id": cluster.cluster_id,
                "fact_type": cluster.fact_type,
                "label": cluster.label,
                "token_signature": cluster.token_signature,
                "paper_count": cluster.paper_count,
                "fact_count": cluster.fact_count,
                "average_confidence": cluster.average_confidence,
                "facts": [
                    {
                        "paper_key": fact.paper_key,
                        "paper_title": fact.paper_title,
                        "year": fact.year,
                        "fact_name": fact.fact_name,
                        "statement": fact.statement,
                        "confidence": fact.confidence,
                        "evidence_source_path": fact.evidence_source_path,
                    }
                    for fact in cluster.facts
                ],
            }
            for cluster in report.clusters
        ],
        "singleton_summaries": [
            {
                "fact_type": summary.fact_type,
                "fact_count": summary.fact_count,
                "paper_count": summary.paper_count,
            }
            for summary in report.singleton_summaries
        ],
    }


def export_research_clusters(
    db_path: Path,
    out_path: Path,
    *,
    output_format: str = "markdown",
    mode: str = "token",
    embedding_provider: EmbeddingProvider | None = None,
    semantic_threshold: float = SEMANTIC_CLUSTER_THRESHOLD,
) -> ResearchClusters:
    report = build_research_clusters(
        db_path,
        mode=mode,
        embedding_provider=embedding_provider,
        semantic_threshold=semantic_threshold,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if output_format == "markdown":
        out_path.write_text(render_markdown(report), encoding="utf-8")
    elif output_format == "json":
        payload = json.dumps(research_clusters_to_dict(report), ensure_ascii=False, indent=2, sort_keys=True)
        out_path.write_text(payload + "\n", encoding="utf-8")
    else:
        raise ValueError(f"unsupported research clusters format: {output_format}")
    return report
