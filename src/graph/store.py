"""
Graph store interface and in-memory implementation for Professor v10.

The graph store is the runtime container for the architecture graph. It provides
a clean interface for adding/retrieving nodes and edges, and supports graph
traversal queries needed by the impact analysis engine.

Phase 1 implementation: InMemoryGraphStore backed by networkx.DiGraph.
Future: Neo4j-backed store for production scale and visualization.

See docs/adr/002-graph-first-architecture.md for the rationale behind
the graph-first approach and the planned evolution to Neo4j.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

import networkx as nx

from src.graph.models import CodeEntity, DependencyEdge, EdgeType, EntityType


class GraphStore(ABC):
    """
    Abstract interface for the architecture graph store.

    All analysis code should depend on this interface, not on the concrete
    InMemoryGraphStore, to enable swapping the storage backend in the future.
    """

    @abstractmethod
    def add_node(self, entity: CodeEntity) -> None:
        """
        Add a code entity as a node in the graph.

        If a node with the same ID already exists, it is replaced.

        Args:
            entity: The CodeEntity to add as a node.
        """
        ...

    @abstractmethod
    def add_edge(self, edge: DependencyEdge) -> None:
        """
        Add a dependency relationship as a directed edge in the graph.

        If an edge with the same ID already exists, it is replaced.

        Args:
            edge: The DependencyEdge to add.
        """
        ...

    @abstractmethod
    def get_node(self, node_id: str) -> CodeEntity | None:
        """
        Retrieve a node by its ID.

        Args:
            node_id: The unique node identifier.

        Returns:
            The CodeEntity if found, None otherwise.
        """
        ...

    @abstractmethod
    def get_neighbors(
        self,
        node_id: str,
        edge_types: list[EdgeType] | None = None,
        direction: str = "out",
    ) -> list[CodeEntity]:
        """
        Retrieve neighboring nodes connected by edges of the given types.

        Args:
            node_id: The node to start from.
            edge_types: Filter to only edges of these types. None means all types.
            direction: 'out' for successors, 'in' for predecessors, 'both' for all.

        Returns:
            List of neighboring CodeEntity objects.
        """
        ...

    @abstractmethod
    def query_path(self, source_id: str, target_id: str) -> list[list[str]]:
        """
        Find all simple paths between two nodes.

        Args:
            source_id: ID of the source node.
            target_id: ID of the target node.

        Returns:
            List of paths, where each path is a list of node IDs.
        """
        ...

    @abstractmethod
    def get_subgraph(self, node_ids: list[str]) -> GraphStore:
        """
        Extract a subgraph containing only the specified nodes and edges between them.

        Args:
            node_ids: List of node IDs to include in the subgraph.

        Returns:
            A new GraphStore containing only the specified nodes.
        """
        ...

    @abstractmethod
    def all_nodes(self) -> list[CodeEntity]:
        """Return all nodes in the graph."""
        ...

    @abstractmethod
    def all_edges(self) -> list[DependencyEdge]:
        """Return all edges in the graph."""
        ...

    @abstractmethod
    def node_count(self) -> int:
        """Return the total number of nodes in the graph."""
        ...

    @abstractmethod
    def edge_count(self) -> int:
        """Return the total number of edges in the graph."""
        ...


class InMemoryGraphStore(GraphStore):
    """
    In-memory architecture graph store backed by networkx.DiGraph.

    This is the Phase 1 implementation. It stores all nodes and edges in memory
    using networkx's directed graph, which supports efficient BFS/DFS traversal
    for impact analysis.

    Limitations:
    - Not persistent across runs (export to JSON for persistence)
    - Memory-bound (suitable for ~10k nodes, which covers most enterprise codebases)
    - No concurrent write support

    See docs/adr/002-graph-first-architecture.md for the Phase 2 migration plan.
    """

    def __init__(self) -> None:
        # networkx DiGraph: nodes keyed by entity ID, edges keyed by (source, target)
        self._graph: nx.DiGraph = nx.DiGraph()
        # Secondary index: entity ID → CodeEntity object (for fast retrieval)
        self._node_index: dict[str, CodeEntity] = {}
        # Secondary index: edge ID → DependencyEdge object
        self._edge_index: dict[str, DependencyEdge] = {}

    def add_node(self, entity: CodeEntity) -> None:
        """
        Add a CodeEntity as a node in the networkx graph.

        The entity is stored as node attribute data, keyed by entity.id.
        """
        self._node_index[entity.id] = entity
        self._graph.add_node(entity.id, entity=entity)

    def add_edge(self, edge: DependencyEdge) -> None:
        """
        Add a DependencyEdge as a directed edge in the networkx graph.

        Both the source and target node IDs must already exist in the graph.
        If they don't exist, the edge is still added but will create implicit
        "placeholder" nodes — a graph completeness warning should be issued.
        """
        # Ensure both endpoints exist as nodes (create placeholder if not)
        if edge.source_id not in self._node_index:
            # TODO: Log a graph completeness warning — source node not found
            pass
        if edge.target_id not in self._node_index:
            # TODO: Log a graph completeness warning — target node not found
            pass

        self._edge_index[edge.id] = edge
        self._graph.add_edge(
            edge.source_id,
            edge.target_id,
            edge_id=edge.id,
            edge_type=edge.edge_type.value,
            edge=edge,
        )

    def get_node(self, node_id: str) -> CodeEntity | None:
        """Retrieve a node by ID from the internal index."""
        return self._node_index.get(node_id)

    def get_neighbors(
        self,
        node_id: str,
        edge_types: list[EdgeType] | None = None,
        direction: str = "out",
    ) -> list[CodeEntity]:
        """
        Retrieve neighboring nodes, optionally filtered by edge type.

        Args:
            node_id: Starting node ID.
            edge_types: If provided, only traverse edges of these types.
            direction: 'out' (successors), 'in' (predecessors), 'both'.

        Returns:
            List of neighboring CodeEntity objects, deduped.
        """
        if node_id not in self._graph:
            return []

        # Collect neighbor node IDs based on direction
        neighbor_ids: set[str] = set()

        if direction in ("out", "both"):
            for _, neighbor_id, edge_data in self._graph.out_edges(node_id, data=True):
                if self._edge_type_matches(edge_data, edge_types):
                    neighbor_ids.add(neighbor_id)

        if direction in ("in", "both"):
            for predecessor_id, _, edge_data in self._graph.in_edges(node_id, data=True):
                if self._edge_type_matches(edge_data, edge_types):
                    neighbor_ids.add(predecessor_id)

        return [self._node_index[nid] for nid in neighbor_ids if nid in self._node_index]

    def query_path(self, source_id: str, target_id: str) -> list[list[str]]:
        """
        Find all simple paths between two nodes using networkx.

        Uses networkx.all_simple_paths with a cutoff to prevent combinatorial
        explosion on densely connected graphs.

        Args:
            source_id: Source node ID.
            target_id: Target node ID.

        Returns:
            List of paths, each path being a list of node IDs from source to target.
        """
        if source_id not in self._graph or target_id not in self._graph:
            return []

        # Cutoff at 8 hops to prevent runaway traversal
        try:
            paths = list(nx.all_simple_paths(self._graph, source_id, target_id, cutoff=8))
            return paths
        except nx.NetworkXError:
            return []

    def get_subgraph(self, node_ids: list[str]) -> InMemoryGraphStore:
        """
        Extract a subgraph containing the specified nodes.

        Creates a new InMemoryGraphStore containing only the specified nodes
        and all edges between them.

        Args:
            node_ids: Node IDs to include.

        Returns:
            New InMemoryGraphStore with the subgraph.
        """
        subgraph = InMemoryGraphStore()

        # Add the specified nodes
        for node_id in node_ids:
            entity = self._node_index.get(node_id)
            if entity:
                subgraph.add_node(entity)

        # Add edges where both endpoints are in the subgraph
        node_set = set(node_ids)
        for edge in self._edge_index.values():
            if edge.source_id in node_set and edge.target_id in node_set:
                subgraph.add_edge(edge)

        return subgraph

    def all_nodes(self) -> list[CodeEntity]:
        """Return all nodes as a list of CodeEntity objects."""
        return list(self._node_index.values())

    def all_edges(self) -> list[DependencyEdge]:
        """Return all edges as a list of DependencyEdge objects."""
        return list(self._edge_index.values())

    def node_count(self) -> int:
        """Return total node count."""
        return len(self._node_index)

    def edge_count(self) -> int:
        """Return total edge count."""
        return len(self._edge_index)

    def to_json(self) -> str:
        """
        Serialize the entire graph to a JSON string.

        Useful for persistence, sharing, and debugging. The JSON can be loaded
        back into an InMemoryGraphStore using from_json().

        Returns:
            JSON string representing the complete graph.
        """
        return json.dumps(
            {
                "nodes": [entity.to_dict() for entity in self._node_index.values()],
                "edges": [edge.to_dict() for edge in self._edge_index.values()],
                "stats": {
                    "node_count": self.node_count(),
                    "edge_count": self.edge_count(),
                },
            },
            indent=2,
        )

    def nodes_by_type(self, entity_type: EntityType) -> list[CodeEntity]:
        """
        Return all nodes of a given entity type.

        Args:
            entity_type: The entity type to filter by.

        Returns:
            List of CodeEntity objects of the specified type.
        """
        return [e for e in self._node_index.values() if e.entity_type == entity_type]

    def nodes_by_repo(self, repo: str) -> list[CodeEntity]:
        """
        Return all nodes belonging to a specific repository.

        Args:
            repo: Repository name to filter by.

        Returns:
            List of CodeEntity objects from the specified repository.
        """
        return [e for e in self._node_index.values() if e.repo == repo]

    def _edge_type_matches(
        self, edge_data: dict[str, Any], edge_types: list[EdgeType] | None
    ) -> bool:
        """
        Check if an edge's type matches the filter list.

        Args:
            edge_data: networkx edge attribute dict.
            edge_types: List of allowed edge types, or None for all types.

        Returns:
            True if the edge should be included.
        """
        if edge_types is None:
            return True
        edge_type_value = edge_data.get("edge_type", "")
        return any(et.value == edge_type_value for et in edge_types)
