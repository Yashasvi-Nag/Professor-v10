"""
Graph query utilities for Professor v10.

Provides high-level query functions over the architecture graph that are used
by the impact analysis engine, the PRD clarifier, and the document generator.

All queries operate on a GraphStore instance and return structured results.
Queries are read-only — they never modify the graph.

Key queries:
- impact_analysis(node_id): Find all transitively affected nodes for a change
- dependency_chain(source, target): Find the dependency path between two nodes
- find_contracts(service): Find all API contracts exposed by a service
- get_cache_dependencies(service): Find all cache keys used by a service
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from src.graph.models import (
    CodeEntity,
    EdgeType,
    EntityType,
    ImpactSeverity,
)
from src.graph.store import GraphStore


@dataclass
class ImpactedNode:
    """
    A single node identified as impacted by a change, with impact metadata.
    """

    entity: CodeEntity
    """The impacted code entity."""

    severity: ImpactSeverity
    """How severely this node is impacted by the change."""

    reason: str
    """Human-readable explanation of why this node is impacted."""

    path_from_seed: list[str] = field(default_factory=list)
    """The sequence of node IDs from the seed (changed) node to this node."""

    hop_count: int = 0
    """Number of hops from the seed node (0 = seed itself)."""


@dataclass
class ImpactAnalysisResult:
    """
    The complete result of an impact analysis query.

    Contains the full set of impacted nodes organized by severity,
    along with metadata about the analysis.
    """

    seed_node_ids: list[str]
    """The node IDs that were the starting point of the analysis (directly changed)."""

    impacted_nodes: list[ImpactedNode]
    """All nodes transitively impacted by the change."""

    total_count: int = 0
    """Total number of impacted nodes."""

    breaking_count: int = 0
    """Number of BREAKING severity impacts."""

    additive_count: int = 0
    """Number of ADDITIVE severity impacts."""

    informational_count: int = 0
    """Number of INFORMATIONAL severity impacts."""

    affected_repos: list[str] = field(default_factory=list)
    """Distinct repositories containing impacted nodes."""

    affected_languages: list[str] = field(default_factory=list)
    """Distinct languages of impacted nodes."""

    warnings: list[str] = field(default_factory=list)
    """Warnings generated during analysis (e.g., unresolved nodes, depth limit reached)."""

    def __post_init__(self) -> None:
        """Compute summary statistics from impacted_nodes list."""
        self.total_count = len(self.impacted_nodes)
        self.breaking_count = sum(
            1 for n in self.impacted_nodes if n.severity == ImpactSeverity.BREAKING
        )
        self.additive_count = sum(
            1 for n in self.impacted_nodes if n.severity == ImpactSeverity.ADDITIVE
        )
        self.informational_count = sum(
            1 for n in self.impacted_nodes if n.severity == ImpactSeverity.INFORMATIONAL
        )
        self.affected_repos = list({n.entity.repo for n in self.impacted_nodes})
        self.affected_languages = list(
            {n.entity.language.value for n in self.impacted_nodes}
        )

    def nodes_by_severity(self, severity: ImpactSeverity) -> list[ImpactedNode]:
        """Filter impacted nodes by severity level."""
        return [n for n in self.impacted_nodes if n.severity == severity]


class GraphQueryEngine:
    """
    High-level query engine for the architecture graph.

    All query methods are pure reads — they do not modify the graph.
    The query engine is the primary interface for analysis modules to
    interrogate the architecture graph.
    """

    # Edge types to follow for different change scenarios.
    # These determine the "blast radius" of a given type of change.
    _IMPACT_EDGES_BY_CHANGE_TYPE: dict[str, list[EdgeType]] = {
        # Adding/modifying a DTO field: affects all consumers via API chain
        "FIELD_CHANGED": [
            EdgeType.MAPS_TO,
            EdgeType.RETURNS,
            EdgeType.CALLS,
            EdgeType.ACCEPTS,
        ],
        # Changing an API endpoint signature: affects all callers
        "API_CHANGED": [
            EdgeType.CALLS,
            EdgeType.EXPOSES,
            EdgeType.RETURNS,
            EdgeType.ACCEPTS,
        ],
        # Changing a cache key: affects all services using that cache
        "CACHE_CHANGED": [EdgeType.USES_CACHE],
        # Changing a Kafka topic schema: affects all producers and consumers
        "KAFKA_CHANGED": [EdgeType.PRODUCES, EdgeType.CONSUMES],
        # Changing a database schema: affects all readers and writers
        "DB_CHANGED": [EdgeType.READS_DB, EdgeType.WRITES_DB],
        # Default: follow all edge types
        "DEFAULT": list(EdgeType),
    }

    def __init__(self, store: GraphStore) -> None:
        """
        Initialize the query engine with a graph store.

        Args:
            store: The GraphStore to query against.
        """
        self._store = store

    def impact_analysis(
        self,
        node_id: str,
        change_type: str = "DEFAULT",
        max_depth: int = 10,
    ) -> ImpactAnalysisResult:
        """
        Compute the full transitive impact set for a change to the given node.

        Performs a bidirectional BFS traversal from the seed node, following
        edges relevant to the specified change type. Classifies each reached
        node by impact severity.

        Args:
            node_id: The ID of the node being changed (the seed node).
            change_type: The type of change being made. Determines which edge
                types are traversed. Options: FIELD_CHANGED, API_CHANGED,
                CACHE_CHANGED, KAFKA_CHANGED, DB_CHANGED, DEFAULT.
            max_depth: Maximum traversal depth to prevent runaway analysis.

        Returns:
            ImpactAnalysisResult with all impacted nodes and severity classifications.
        """
        seed_node = self._store.get_node(node_id)
        if seed_node is None:
            return ImpactAnalysisResult(
                seed_node_ids=[node_id],
                impacted_nodes=[],
                warnings=[f"Seed node '{node_id}' not found in graph"],
            )

        edge_types = self._IMPACT_EDGES_BY_CHANGE_TYPE.get(
            change_type, self._IMPACT_EDGES_BY_CHANGE_TYPE["DEFAULT"]
        )

        impacted: list[ImpactedNode] = []
        visited: set[str] = {node_id}
        warnings: list[str] = []

        # BFS queue: (current_node_id, path_from_seed, hop_count, direction)
        queue: deque[tuple[str, list[str], int, str]] = deque()
        queue.append((node_id, [node_id], 0, "both"))

        while queue:
            current_id, path, depth, direction = queue.popleft()

            if depth >= max_depth:
                warnings.append(
                    f"Max traversal depth ({max_depth}) reached at node '{current_id}'. "
                    "Some downstream impacts may not be reported."
                )
                continue

            # Get neighbors in the relevant direction
            neighbors = self._store.get_neighbors(
                current_id, edge_types=edge_types, direction=direction
            )

            for neighbor in neighbors:
                if neighbor.id in visited:
                    continue
                visited.add(neighbor.id)

                # Classify impact severity for this neighbor
                severity, reason = self._classify_impact(
                    seed_node=seed_node,
                    impacted_node=neighbor,
                    change_type=change_type,
                    hop_count=depth + 1,
                )

                impacted.append(
                    ImpactedNode(
                        entity=neighbor,
                        severity=severity,
                        reason=reason,
                        path_from_seed=path + [neighbor.id],
                        hop_count=depth + 1,
                    )
                )

                # Continue traversal
                queue.append((neighbor.id, path + [neighbor.id], depth + 1, direction))

        return ImpactAnalysisResult(
            seed_node_ids=[node_id],
            impacted_nodes=impacted,
            warnings=warnings,
        )

    def dependency_chain(
        self, source_id: str, target_id: str
    ) -> list[list[CodeEntity]]:
        """
        Find all dependency paths between two nodes in the graph.

        Useful for answering: "How does service A depend on service B?"
        or "What is the chain from frontend model to backend database?"

        Args:
            source_id: Starting node ID.
            target_id: Destination node ID.

        Returns:
            List of paths, where each path is a list of CodeEntity objects
            from source to target. Empty list if no path exists.
        """
        raw_paths = self._store.query_path(source_id, target_id)
        result = []
        for path in raw_paths:
            entity_path = []
            for node_id in path:
                entity = self._store.get_node(node_id)
                if entity:
                    entity_path.append(entity)
            if entity_path:
                result.append(entity_path)
        return result

    def find_contracts(self, service_id: str) -> list[CodeEntity]:
        """
        Find all API contracts (endpoints) exposed by a given service.

        Returns all EndpointNode objects reachable from the service via
        EXPOSES edges.

        Args:
            service_id: The ID of the service node.

        Returns:
            List of EndpointNode objects representing the service's API surface.
        """
        return self._store.get_neighbors(
            service_id,
            edge_types=[EdgeType.EXPOSES],
            direction="out",
        )

    def get_cache_dependencies(self, service_id: str) -> list[CodeEntity]:
        """
        Find all cache keys/regions used by a given service.

        Returns all CacheNode objects connected to the service via USES_CACHE edges.

        Args:
            service_id: The ID of the service node.

        Returns:
            List of CacheNode objects representing the service's cache usage.
        """
        return self._store.get_neighbors(
            service_id,
            edge_types=[EdgeType.USES_CACHE],
            direction="out",
        )

    def find_service_consumers(self, service_id: str) -> list[CodeEntity]:
        """
        Find all services that call the given service (reverse CALLS lookup).

        Args:
            service_id: The ID of the service being consumed.

        Returns:
            List of ServiceNode objects that call this service.
        """
        return self._store.get_neighbors(
            service_id,
            edge_types=[EdgeType.CALLS],
            direction="in",
        )

    def find_model_mappings(self, model_id: str) -> list[CodeEntity]:
        """
        Find all cross-language model mappings for a given model.

        For a Java DTO, returns the Dart models and TypeScript interfaces
        that are linked via MAPS_TO edges.

        Args:
            model_id: The ID of the source model (typically the Java DTO).

        Returns:
            List of ModelNode objects in other languages that map to this model.
        """
        return self._store.get_neighbors(
            model_id,
            edge_types=[EdgeType.MAPS_TO],
            direction="both",
        )

    def orphan_nodes(self) -> list[CodeEntity]:
        """
        Find all nodes with no edges (isolated nodes in the graph).

        Orphan nodes are a graph completeness warning — they may indicate
        a parsing gap (a service that was detected but its relationships
        were not resolved).

        Returns:
            List of CodeEntity objects with no incoming or outgoing edges.
        """
        return [
            entity
            for entity in self._store.all_nodes()
            if not self._store.get_neighbors(entity.id, direction="both")
        ]

    def _classify_impact(
        self,
        seed_node: CodeEntity,
        impacted_node: CodeEntity,
        change_type: str,
        hop_count: int,
    ) -> tuple[ImpactSeverity, str]:
        """
        Classify the impact severity of a node reached during traversal.

        Classification rules (see docs/design/05-change-impact-propagation.md):
        - BREAKING: The consumer cannot function without a code change
        - ADDITIVE: The consumer should be updated but can still function
        - INFORMATIONAL: Awareness only, no code change required

        Args:
            seed_node: The originally changed node.
            impacted_node: The node whose impact is being classified.
            change_type: The type of change being analyzed.
            hop_count: How many hops from the seed node.

        Returns:
            Tuple of (ImpactSeverity, reason_string).
        """
        # TODO: Implement detailed classification rules
        # Current placeholder: classify by entity type and hop count
        #
        # Rules to implement:
        # 1. FIELD_CHANGED + required field added:
        #    - Direct DTO consumers (hop 1): BREAKING
        #    - Frontend models (hop 2 via MAPS_TO): ADDITIVE (nullable field safe)
        #    - Cache nodes: INFORMATIONAL (cached response will include new field)
        # 2. API_CHANGED + path changed:
        #    - All CALLS consumers: BREAKING
        # 3. KAFKA_CHANGED + schema change:
        #    - All CONSUMES consumers: BREAKING (if required field)
        # 4. For hop_count > 3: downgrade severity by one level

        if impacted_node.entity_type in (EntityType.CACHE, EntityType.MESSAGE_TOPIC):
            return ImpactSeverity.INFORMATIONAL, (
                f"Cache/messaging node may need refresh due to change in {seed_node.name}"
            )

        if hop_count == 1:
            return ImpactSeverity.ADDITIVE, (
                f"Directly depends on changed entity '{seed_node.name}'"
            )

        return ImpactSeverity.ADDITIVE, (
            f"Transitively impacted via {hop_count}-hop dependency chain from '{seed_node.name}'"
        )
