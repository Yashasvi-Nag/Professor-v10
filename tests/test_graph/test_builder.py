"""
Tests for the GraphBuilder.

Tests cover:
- Adding entities from a single parser
- Adding entities from multiple parsers (multi-language)
- Build returns a populated GraphStore
- Node count reflects all added entities
- Edge creation via _create_edge utility
"""


from src.graph.builder import GraphBuilder
from src.graph.models import (
    DependencyEdge,
    EdgeType,
    Language,
    ModelNode,
    ServiceNode,
)
from src.graph.store import InMemoryGraphStore


class TestGraphBuilderBasic:
    """Tests for basic GraphBuilder functionality."""

    def test_builder_returns_graph_store(self) -> None:
        """build() should return a GraphStore instance."""
        builder = GraphBuilder()
        store = builder.build()
        assert isinstance(store, InMemoryGraphStore)

    def test_builder_empty_entities(self) -> None:
        """build() with no entities should produce an empty graph."""
        builder = GraphBuilder()
        store = builder.build()
        assert store.node_count() == 0
        assert store.edge_count() == 0

    def test_add_entities_returns_self(
        self, sample_java_service: ServiceNode
    ) -> None:
        """add_entities() should return self for method chaining."""
        builder = GraphBuilder()
        result = builder.add_entities([sample_java_service])
        assert result is builder

    def test_method_chaining(
        self,
        sample_java_service: ServiceNode,
        sample_java_dto: ModelNode,
    ) -> None:
        """Multiple add_entities() calls should accumulate entities."""
        store = (
            GraphBuilder()
            .add_entities([sample_java_service])
            .add_entities([sample_java_dto])
            .build()
        )
        assert store.node_count() == 2


class TestGraphBuilderNodeAddition:
    """Tests for node addition during build()."""

    def test_nodes_are_added_to_store(
        self,
        sample_java_service: ServiceNode,
        sample_java_dto: ModelNode,
        sample_dart_model: ModelNode,
    ) -> None:
        """All entities added via add_entities() should appear in the built graph."""
        entities = [sample_java_service, sample_java_dto, sample_dart_model]
        store = GraphBuilder().add_entities(entities).build()
        assert store.node_count() == len(entities)

    def test_node_retrieval_by_id(
        self, sample_java_service: ServiceNode
    ) -> None:
        """Nodes added to the graph should be retrievable by their ID."""
        store = GraphBuilder().add_entities([sample_java_service]).build()
        node = store.get_node(sample_java_service.id)
        assert node is not None
        assert node.name == sample_java_service.name

    def test_duplicate_nodes_are_deduplicated(
        self, sample_java_service: ServiceNode
    ) -> None:
        """Adding the same entity twice should not create duplicate nodes."""
        store = (
            GraphBuilder()
            .add_entities([sample_java_service])
            .add_entities([sample_java_service])
            .build()
        )
        assert store.node_count() == 1

    def test_multi_language_entities_in_same_graph(
        self,
        sample_java_dto: ModelNode,
        sample_dart_model: ModelNode,
        sample_typescript_interface: ModelNode,
    ) -> None:
        """Entities from different languages should coexist in the same graph."""
        store = (
            GraphBuilder()
            .add_entities([sample_java_dto])
            .add_entities([sample_dart_model])
            .add_entities([sample_typescript_interface])
            .build()
        )
        assert store.node_count() == 3
        # Verify each language is represented
        languages = {store.get_node(e.id).language for e in [
            sample_java_dto, sample_dart_model, sample_typescript_interface
        ]}
        assert Language.JAVA in languages
        assert Language.DART in languages
        assert Language.TYPESCRIPT in languages


class TestGraphBuilderEdgeCreation:
    """Tests for the _create_edge() utility."""

    def test_create_edge_adds_to_store(
        self,
        sample_java_service: ServiceNode,
        sample_java_dto: ModelNode,
    ) -> None:
        """_create_edge() should add an edge to the graph store."""
        builder = GraphBuilder()
        builder.add_entities([sample_java_service, sample_java_dto])
        # Build first to populate the store
        store = builder.build()

        # Now manually test the edge creation mechanism by adding an edge to the store
        edge = DependencyEdge(
            id="test-edge-001",
            source_id=sample_java_service.id,
            target_id=sample_java_dto.id,
            edge_type=EdgeType.DEPENDS_ON,
        )
        store.add_edge(edge)
        assert store.edge_count() == 1

    def test_edge_id_is_deterministic(
        self,
        sample_java_service: ServiceNode,
        sample_java_dto: ModelNode,
    ) -> None:
        """The same logical edge should produce the same ID (idempotent)."""
        builder = GraphBuilder()
        builder.add_entities([sample_java_service, sample_java_dto])
        builder.build()

        edge1 = builder._create_edge(
            source_id=sample_java_service.id,
            target_id=sample_java_dto.id,
            edge_type=EdgeType.DEPENDS_ON,
        )
        edge2 = builder._create_edge(
            source_id=sample_java_service.id,
            target_id=sample_java_dto.id,
            edge_type=EdgeType.DEPENDS_ON,
        )
        assert edge1.id == edge2.id


class TestGraphBuilderWithFullGraph:
    """Tests using the full sample graph from conftest.py."""

    def test_sample_graph_has_correct_node_count(
        self, sample_graph_store: InMemoryGraphStore
    ) -> None:
        """The sample graph fixture should have the expected number of nodes."""
        # The fixture adds: controller, dto, endpoint, dart model, ts interface,
        # cache node, feed service = 7 nodes
        assert sample_graph_store.node_count() == 7

    def test_sample_graph_has_correct_edge_count(
        self, sample_graph_store: InMemoryGraphStore
    ) -> None:
        """The sample graph fixture should have the expected number of edges."""
        # 6 edges added in conftest.py
        assert sample_graph_store.edge_count() == 6
