"""
Change impact analysis engine for Professor v10.

This module orchestrates the full impact analysis workflow:
1. Parse a change description to identify seed nodes
2. Use GraphQueryEngine to compute the transitive impact set
3. Enrich each impacted node with action items and evidence links
4. Produce a structured ImpactReport suitable for document generation

The ImpactAnalyzer is the highest-level analysis component — it sits above
the GraphQueryEngine and adds business-logic classification on top of
raw graph traversal.

See docs/design/05-change-impact-propagation.md for the full algorithm design.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.graph.models import (
    CodeEntity,
    EntityType,
    ImpactSeverity,
    Language,
)
from src.graph.query import GraphQueryEngine, ImpactAnalysisResult, ImpactedNode
from src.graph.store import GraphStore


@dataclass
class ActionItem:
    """
    A concrete action required as a result of a change impact.

    Action items are the actionable output of impact analysis — they tell
    engineers exactly what needs to change and where.
    """

    description: str
    """What needs to be done (e.g., "Add estimatedSavings field (nullable double)")."""

    entity: CodeEntity
    """The entity that requires the action."""

    severity: ImpactSeverity
    """Severity of the impact driving this action."""

    file_path: str = ""
    """The specific file to change."""

    estimated_effort: str = "low"
    """Rough effort estimate: 'low', 'medium', 'high'."""


@dataclass
class ImpactReport:
    """
    The complete structured impact report for a proposed change.

    This is the primary output of the ImpactAnalyzer and the primary input
    to the document generator. It contains all information needed to produce
    a complete architectural change document.

    See docs/design/05-change-impact-propagation.md for the report structure.
    """

    feature_id: str
    """Identifier linking this report to a feature request or PRD."""

    change_summary: str
    """One-line description of the change being analyzed."""

    seed_nodes: list[CodeEntity]
    """The code entities directly changed by this feature."""

    impact_result: ImpactAnalysisResult
    """The raw impact analysis result from GraphQueryEngine."""

    action_items: list[ActionItem] = field(default_factory=list)
    """Concrete actions required, derived from the impact analysis."""

    risks: list[str] = field(default_factory=list)
    """Known risks and caveats for this change."""

    rollout_notes: list[str] = field(default_factory=list)
    """Recommended rollout strategy notes."""

    @property
    def affected_services(self) -> list[CodeEntity]:
        """Return all impacted nodes that are services or controllers."""
        return [
            n.entity
            for n in self.impact_result.impacted_nodes
            if n.entity.entity_type in (EntityType.SERVICE, EntityType.CONTROLLER)
        ]

    @property
    def affected_models(self) -> list[CodeEntity]:
        """Return all impacted nodes that are data models or DTOs."""
        return [
            n.entity
            for n in self.impact_result.impacted_nodes
            if n.entity.entity_type in (EntityType.MODEL, EntityType.DTO, EntityType.ENTITY)
        ]

    @property
    def affected_endpoints(self) -> list[CodeEntity]:
        """Return all impacted nodes that are API endpoints."""
        return [
            n.entity
            for n in self.impact_result.impacted_nodes
            if n.entity.entity_type == EntityType.ENDPOINT
        ]

    @property
    def affected_caches(self) -> list[CodeEntity]:
        """Return all impacted cache nodes."""
        return [
            n.entity
            for n in self.impact_result.impacted_nodes
            if n.entity.entity_type == EntityType.CACHE
        ]

    @property
    def affected_databases(self) -> list[CodeEntity]:
        """Return all impacted database nodes."""
        return [
            n.entity
            for n in self.impact_result.impacted_nodes
            if n.entity.entity_type == EntityType.DATABASE
        ]


class ImpactAnalyzer:
    """
    Orchestrates the full change impact analysis workflow.

    Sits above the GraphQueryEngine and adds:
    - Change description parsing to identify seed nodes
    - Action item generation per impacted node
    - Risk identification based on impact patterns
    - Rollout strategy recommendations

    Usage:
        analyzer = ImpactAnalyzer(graph_store)
        report = analyzer.analyze(
            feature_id="FEAT-001",
            change_summary="Add estimatedSavings field to CouponResponseDto",
            seed_node_ids=["coupon-engine/java/dto/CouponResponseDto"],
            change_type="FIELD_CHANGED"
        )
    """

    def __init__(self, store: GraphStore) -> None:
        """
        Initialize the analyzer with a populated graph store.

        Args:
            store: The architecture graph store to analyze against.
        """
        self._store = store
        self._query_engine = GraphQueryEngine(store)

    def analyze(
        self,
        feature_id: str,
        change_summary: str,
        seed_node_ids: list[str],
        change_type: str = "DEFAULT",
        max_depth: int = 10,
    ) -> ImpactReport:
        """
        Run the full impact analysis for a proposed change.

        Args:
            feature_id: Identifier for the feature/PRD driving this change.
            change_summary: Human-readable description of what is changing.
            seed_node_ids: IDs of graph nodes directly affected by the change.
                These are the starting points for impact traversal.
            change_type: The type of change (FIELD_CHANGED, API_CHANGED, etc.)
                Determines which edge types are followed during traversal.
            max_depth: Maximum traversal depth.

        Returns:
            ImpactReport with complete impact analysis, action items, and risks.
        """
        # Resolve seed node IDs to CodeEntity objects
        seed_nodes = []
        for node_id in seed_node_ids:
            node = self._store.get_node(node_id)
            if node:
                seed_nodes.append(node)
            # TODO: Log warning if seed node not found in graph

        # Run multi-seed impact analysis (union of individual analyses)
        all_impacted: list[ImpactedNode] = []
        all_warnings: list[str] = []
        visited_ids: set[str] = set(seed_node_ids)

        for node_id in seed_node_ids:
            result = self._query_engine.impact_analysis(
                node_id=node_id,
                change_type=change_type,
                max_depth=max_depth,
            )
            # Deduplicate: only add nodes not already seen from another seed
            for impacted_node in result.impacted_nodes:
                if impacted_node.entity.id not in visited_ids:
                    visited_ids.add(impacted_node.entity.id)
                    all_impacted.append(impacted_node)
            all_warnings.extend(result.warnings)

        # Rebuild a combined ImpactAnalysisResult
        from src.graph.query import ImpactAnalysisResult  # noqa: PLC0415

        combined_result = ImpactAnalysisResult(
            seed_node_ids=seed_node_ids,
            impacted_nodes=all_impacted,
            warnings=all_warnings,
        )

        # Generate action items for each impacted node
        action_items = self._generate_action_items(all_impacted, change_summary)

        # Identify risks from impact patterns
        risks = self._identify_risks(combined_result)

        # Generate rollout notes
        rollout_notes = self._generate_rollout_notes(combined_result)

        return ImpactReport(
            feature_id=feature_id,
            change_summary=change_summary,
            seed_nodes=seed_nodes,
            impact_result=combined_result,
            action_items=action_items,
            risks=risks,
            rollout_notes=rollout_notes,
        )

    def find_seed_nodes(
        self,
        change_description: str,
        hints: list[str] | None = None,
    ) -> list[str]:
        """
        Identify seed node IDs from a natural language change description.

        Searches the graph for nodes whose names match entities mentioned in
        the change description. Returns a list of candidate seed node IDs
        for use in the analyze() call.

        Args:
            change_description: Natural language description of the change.
                Example: "Add estimatedSavings to CouponResponseDto"
            hints: Optional list of entity names or node IDs to prioritize.

        Returns:
            List of node IDs that are candidate seed nodes.
        """
        # TODO: Implement intelligent seed node identification
        # Algorithm:
        # 1. Extract entity names from change_description using regex/NLP:
        #    - PascalCase words → likely class/DTO names
        #    - camelCase words → likely field names
        #    - "service", "endpoint", "API" keywords → narrow to specific entity types
        # 2. Search graph for nodes whose name matches extracted names (fuzzy matching)
        # 3. Apply hints as additional search keys
        # 4. Rank candidates by confidence:
        #    - Exact name match in same domain: highest confidence
        #    - Partial name match: medium confidence
        #    - Domain-only match: lowest confidence
        # 5. Return top N candidates (configurable, default: top 5)
        #
        # Example: "Add estimatedSavings to CouponResponseDto"
        # → Search for nodes named "CouponResponseDto"
        # → Returns: ["coupon-engine/java/dto/CouponResponseDto"]

        return hints or []

    def _generate_action_items(
        self,
        impacted_nodes: list[ImpactedNode],
        change_summary: str,
    ) -> list[ActionItem]:
        """
        Generate concrete action items for each impacted node.

        Produces human-readable, entity-specific action descriptions that
        tell engineers exactly what to change and where.

        Args:
            impacted_nodes: List of impacted nodes from the analysis.
            change_summary: The change description for context.

        Returns:
            List of ActionItem objects, one per impacted node requiring action.
        """
        # TODO: Implement action item generation
        # For each impacted node, generate an action based on:
        # - EntityType: DTO → "Add field X (type T)", API → "Update endpoint signature"
        # - Language: Java → "Add field to Java class", Dart → "Add field to Dart model"
        # - Severity: BREAKING → include migration guidance
        # - Cache: → "Invalidate/update cache key pattern"
        # - Kafka: → "Update message schema, coordinate with consumers"
        #
        # Example actions:
        # - ModelNode (Dart): "Add `estimatedSavings` field (nullable double?) to CouponModel"
        # - ModelNode (TS): "Add `estimatedSavings?: number` to CouponDto interface"
        # - CacheNode: "Update cache key or invalidate 'feed:{userId}' entries"
        # - EndpointNode: "Verify /api/feed response contract includes estimatedSavings"
        return []

    def _identify_risks(self, result: ImpactAnalysisResult) -> list[str]:
        """
        Identify architectural risks based on the impact analysis results.

        Produces a list of risk statements to include in the impact report,
        drawing on patterns in the impacted node set.

        Args:
            result: The complete impact analysis result.

        Returns:
            List of risk strings for inclusion in the output document.
        """
        risks = []

        # TODO: Implement risk identification rules
        # Risk patterns to detect:
        # 1. Multiple breaking impacts → high-coordination risk
        # 2. Cache nodes impacted → stale data risk during rollout
        # 3. Kafka consumers impacted → message schema migration risk
        # 4. Mobile (Dart) models impacted → old app version backward compat risk
        # 5. Multiple repos impacted → cross-team coordination required
        # 6. Database nodes impacted → migration risk, potential downtime

        if result.breaking_count > 0:
            risks.append(
                f"{result.breaking_count} breaking impact(s) detected. "
                "Coordinate deployment order with dependent service teams."
            )

        if result.affected_repos and len(result.affected_repos) > 2:
            risks.append(
                f"Change spans {len(result.affected_repos)} repositories "
                f"({', '.join(result.affected_repos)}). "
                "Cross-team coordination required."
            )

        dart_impacts = [
            n for n in result.impacted_nodes
            if n.entity.language == Language.DART
        ]
        if dart_impacts:
            risks.append(
                "Mobile (Flutter) models are impacted. Ensure the new field is nullable "
                "to maintain backward compatibility with older app versions in production."
            )

        return risks

    def _generate_rollout_notes(self, result: ImpactAnalysisResult) -> list[str]:
        """
        Generate rollout strategy recommendations based on impact analysis.

        Args:
            result: The complete impact analysis result.

        Returns:
            List of rollout recommendation strings.
        """
        notes = []

        # TODO: Implement rollout strategy recommendations
        # Patterns to detect:
        # 1. Breaking backend API change → backend must deploy before frontend
        # 2. Additive change (nullable field) → safe to deploy in any order
        # 3. Cache impact → plan cache warm-up or accept cold cache period
        # 4. Kafka schema change → consider schema registry migration
        # 5. Multi-repo → recommend phased rollout with feature flags

        if result.breaking_count == 0 and result.additive_count > 0:
            notes.append(
                "Change is additive (no breaking impacts). "
                "Can be deployed to backend first, then frontend."
            )

        cache_impacts = [
            n for n in result.impacted_nodes
            if n.entity.entity_type == EntityType.CACHE
        ]
        if cache_impacts:
            notes.append(
                "Cache entries will contain stale data until TTL expires or explicit invalidation. "
                "Consider planned cache invalidation as part of deployment."
            )

        return notes
