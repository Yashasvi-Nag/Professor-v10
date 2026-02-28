"""
Architecture graph builder for Professor v10.

The GraphBuilder takes parsed CodeEntity objects from one or more language-specific
parsers and assembles them into a unified architecture graph. It is responsible for:
1. Adding all entity nodes to the graph store
2. Resolving cross-entity relationships and creating edges
3. Performing cross-language schema alignment (linking Java DTOs to Dart/TS models)
4. Inferring implicit relationships (e.g., Feign client → matching controller)

The builder operates in two passes:
- Pass 1: Add all nodes from all parsers (language-agnostic)
- Pass 2: Resolve relationships and create edges (requires all nodes to be present)

See docs/design/01-code-graph-extraction.md and docs/design/02-cross-language-schema-alignment.md.
"""

import hashlib
from collections import defaultdict

from src.graph.models import (
    CodeEntity,
    DependencyEdge,
    EdgeType,
    EndpointNode,
    ModelNode,
    SourceLocation,
)
from src.graph.store import GraphStore, InMemoryGraphStore


class GraphBuilder:
    """
    Constructs the architecture graph from parsed code entities.

    Usage:
        builder = GraphBuilder()
        builder.add_entities(java_parser.parse("/path/to/java-service"))
        builder.add_entities(dart_parser.parse("/path/to/flutter-app"))
        builder.add_entities(ts_parser.parse("/path/to/angular-admin"))
        graph = builder.build()
    """

    def __init__(self, store: GraphStore | None = None) -> None:
        """
        Initialize the GraphBuilder.

        Args:
            store: The graph store to use. Defaults to InMemoryGraphStore.
        """
        self._store: GraphStore = store or InMemoryGraphStore()
        self._pending_entities: list[CodeEntity] = []
        self._endpoint_index: dict[str, EndpointNode] = {}  # path → endpoint node
        self._model_index: dict[str, list[ModelNode]] = defaultdict(list)  # name → models

    def add_entities(self, entities: list[CodeEntity]) -> "GraphBuilder":
        """
        Register parsed entities to be added to the graph.

        Multiple calls to add_entities() accumulate entities from different
        parsers/repos. All entities are processed together when build() is called,
        enabling cross-language relationship resolution.

        Args:
            entities: List of CodeEntity objects from a parser.

        Returns:
            self (for method chaining).
        """
        self._pending_entities.extend(entities)
        return self

    def build(self) -> GraphStore:
        """
        Build the complete architecture graph from all added entities.

        Executes two passes:
        1. Add all nodes to the graph store and build lookup indexes
        2. Resolve relationships and add edges

        Returns:
            The populated GraphStore containing all nodes and edges.
        """
        # Pass 1: Add all nodes and build lookup indexes
        self._add_all_nodes()

        # Pass 2: Resolve relationships and add edges
        self._resolve_endpoint_relationships()
        self._resolve_feign_client_relationships()
        self._resolve_kafka_relationships()
        self._resolve_cross_language_model_mappings()
        self._resolve_cache_relationships()
        self._resolve_database_relationships()

        return self._store

    # -------------------------------------------------------------------------
    # Pass 1: Node addition
    # -------------------------------------------------------------------------

    def _add_all_nodes(self) -> None:
        """
        Add all pending entities to the graph store and build lookup indexes.

        Also builds secondary indexes (endpoint_index, model_index) used
        during relationship resolution in Pass 2.
        """
        for entity in self._pending_entities:
            self._store.add_node(entity)

            # Build endpoint index: HTTP path → EndpointNode
            # Used to match Feign clients / HTTP client calls to server endpoints
            if isinstance(entity, EndpointNode) and not entity.is_consumer:
                self._endpoint_index[entity.path] = entity

            # Build model index: model name (lowercase) → list of ModelNode
            # Used for cross-language schema alignment
            if isinstance(entity, ModelNode):
                self._model_index[entity.name.lower()].append(entity)

    # -------------------------------------------------------------------------
    # Pass 2: Relationship resolution
    # -------------------------------------------------------------------------

    def _resolve_endpoint_relationships(self) -> None:
        """
        Create EXPOSES edges between controllers and their endpoints.

        For each EndpointNode, find the controller that declares it (they should
        be in the same file) and create a CONTROLLER → EXPOSES → ENDPOINT edge.

        Also creates RETURNS edges between endpoints and their response DTOs
        when the response_dto field is populated.
        """
        # TODO: Implement endpoint → controller relationship resolution
        # Algorithm:
        # 1. For each EndpointNode (is_consumer=False):
        #    a. Find all ServiceNode(entity_type=CONTROLLER) in the same file
        #    b. Create edge: controller EXPOSES endpoint
        # 2. For each EndpointNode with response_dto set:
        #    a. Find ModelNode with matching name in the same repo
        #    b. Create edge: endpoint RETURNS model
        # 3. For each EndpointNode with request_dto set:
        #    a. Find ModelNode with matching name in the same repo
        #    b. Create edge: endpoint ACCEPTS model

    def _resolve_feign_client_relationships(self) -> None:
        """
        Create CALLS edges between Feign client consumers and server endpoints.

        For each EndpointNode with is_consumer=True (representing a Feign client
        or HTTP client call), find the matching server-side EndpointNode by
        matching the HTTP method and path, then create the appropriate edge.

        This is the primary mechanism for building the service-to-service
        dependency graph for synchronous REST calls.
        """
        # TODO: Implement Feign client → server endpoint resolution
        # Algorithm:
        # 1. Collect all consumer EndpointNodes (is_consumer=True)
        # 2. For each consumer endpoint:
        #    a. Normalize the path (strip path parameters, lowercase)
        #    b. Find matching server endpoint in endpoint_index
        #    c. Find the ServiceNode that declares the consumer (same file/class)
        #    d. Find the ServiceNode that declares the server endpoint (same file/class)
        #    e. Create edge: consumer_service CALLS server_service
        #       with metadata: {http_method, endpoint_path, feign_client_class}
        # 3. Log unresolved Feign clients (no matching server endpoint found)
        #    as graph completeness warnings

    def _resolve_kafka_relationships(self) -> None:
        """
        Create PRODUCES and CONSUMES edges between services and Kafka topics.

        Groups MessageTopicNode objects by their topic_name, then creates:
        - service PRODUCES message_topic_node (for producer nodes)
        - service CONSUMES message_topic_node (for consumer nodes)

        Also creates a synthetic "topic" node if multiple services interact
        with the same topic — this becomes the central hub for that topic's
        impact analysis.
        """
        # TODO: Implement Kafka producer/consumer relationship resolution
        # Algorithm:
        # 1. Group all MessageTopicNode objects by topic_name
        # 2. For each topic:
        #    a. Create a synthetic "TOPIC" node representing the topic itself
        #    b. For each producer node: producer_service PRODUCES topic_node
        #    c. For each consumer node: topic_node CONSUMES consumer_service
        # 3. Producer and consumer groups with the same topic_name are linked
        #    via the topic node, enabling full producer→topic→consumer traversal

    def _resolve_cross_language_model_mappings(self) -> None:
        """
        Create MAPS_TO edges between Java DTOs and their Dart/TypeScript counterparts.

        This is the cross-language schema alignment step. It uses name matching
        (with normalization) as the primary strategy, with API endpoint contract
        tracing as a secondary validation signal.

        See docs/design/02-cross-language-schema-alignment.md for full strategy.
        """
        # TODO: Implement cross-language model mapping
        # Algorithm:
        # 1. Group all ModelNode objects by normalized name
        #    Normalization: remove "Dto", "Model", "Interface", "Response" suffixes,
        #    convert to lowercase, strip language-specific patterns
        # 2. For each group with models from multiple languages:
        #    a. Identify the "source of truth" (Java DTO if present, otherwise first found)
        #    b. Create edges: java_dto MAPS_TO dart_model, java_dto MAPS_TO ts_interface
        # 3. API contract tracing (secondary validation):
        #    For endpoints that share the same URL path across Java (returns) and
        #    Dart/TS (consumes), the response DTOs are likely the same entity.
        #    Use this to create or confirm MAPS_TO edges.
        # 4. Record alignment confidence:
        #    - Exact name match (after normalization): 0.85
        #    - API endpoint URL match: 0.90
        #    - Both name + URL match: 0.95
        #    - Manual override in config: 1.00

    def _resolve_cache_relationships(self) -> None:
        """
        Create USES_CACHE edges between services and cache nodes.

        For each CacheNode, find the service that declares it (by file path
        or class context) and create an appropriate edge.
        """
        # TODO: Implement cache relationship resolution
        # Algorithm:
        # 1. For each CacheNode:
        #    a. Find the ServiceNode in the same file/class
        #    b. Create edge: service USES_CACHE cache_node
        #       with metadata: {operation: "read|write|evict", cache_key, ttl}

    def _resolve_database_relationships(self) -> None:
        """
        Create READS_DB and WRITES_DB edges between repositories and database nodes.

        For each DatabaseNode, find the repository or service that interacts with it
        and create directed edges based on the detected operation type.
        """
        # TODO: Implement database relationship resolution
        # Algorithm:
        # 1. For each DatabaseNode with operations detected:
        #    a. Find the Repository or Service in the same file
        #    b. For SELECT operations: repository READS_DB database_node
        #    c. For INSERT/UPDATE/DELETE: repository WRITES_DB database_node

    # -------------------------------------------------------------------------
    # Edge creation utilities
    # -------------------------------------------------------------------------

    def _create_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: EdgeType,
        metadata: dict | None = None,
        source_location: SourceLocation | None = None,
        confidence: float = 1.0,
    ) -> DependencyEdge:
        """
        Create a DependencyEdge with a deterministic ID and add it to the store.

        The edge ID is computed as a hash of source + edge_type + target, ensuring
        idempotent edge creation (adding the same logical edge twice has no effect).

        Args:
            source_id: ID of the source node.
            target_id: ID of the target node.
            edge_type: The semantic type of the relationship.
            metadata: Optional additional context for the edge.
            source_location: Where in the code this relationship is declared.
            confidence: Detection confidence score (0.0–1.0).

        Returns:
            The created DependencyEdge.
        """
        edge_key = f"{source_id}|{edge_type.value}|{target_id}"
        edge_id = hashlib.sha256(edge_key.encode()).hexdigest()[:12]

        edge = DependencyEdge(
            id=edge_id,
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type,
            metadata=metadata or {},
            source_location=source_location,
            confidence=confidence,
        )
        self._store.add_edge(edge)
        return edge
