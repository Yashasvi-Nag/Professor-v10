"""
Tests for graph models (nodes and edges).

Tests cover:
- CodeEntity base class behavior
- Subclass instantiation (ServiceNode, EndpointNode, ModelNode, etc.)
- SourceLocation string formatting
- EntityType and EdgeType enum values
- to_dict() serialization
- DependencyEdge creation and serialization
"""


from src.graph.models import (
    CacheNode,
    DependencyEdge,
    EdgeType,
    EndpointNode,
    EntityType,
    ImpactSeverity,
    Language,
    MessageTopicNode,
    ModelNode,
    ServiceNode,
    SourceLocation,
)


class TestSourceLocation:
    """Tests for the SourceLocation dataclass."""

    def test_str_format_with_all_fields(self) -> None:
        loc = SourceLocation(
            repo="coupon-engine",
            file_path="src/main/java/CouponController.java",
            line_number=42,
            commit_sha="abc123def456",
        )
        result = str(loc)
        assert "coupon-engine" in result
        assert "CouponController.java" in result
        assert "42" in result
        assert "abc123de" in result  # First 8 chars of commit SHA

    def test_str_format_without_commit(self) -> None:
        loc = SourceLocation(
            repo="coupon-engine",
            file_path="src/main/java/CouponController.java",
            line_number=42,
        )
        result = str(loc)
        assert "@" not in result  # No commit SHA separator

    def test_default_line_number_is_zero(self) -> None:
        loc = SourceLocation(repo="repo", file_path="file.java")
        assert loc.line_number == 0


class TestCodeEntity:
    """Tests for the CodeEntity base class."""

    def test_source_location_property(self, sample_java_service: ServiceNode) -> None:
        """source_location property should return a valid SourceLocation."""
        loc = sample_java_service.source_location
        assert isinstance(loc, SourceLocation)
        assert loc.repo == sample_java_service.repo
        assert loc.file_path == sample_java_service.file_path
        assert loc.line_number == sample_java_service.line_number

    def test_to_dict_contains_required_fields(
        self, sample_java_service: ServiceNode
    ) -> None:
        """to_dict() should contain all required fields."""
        d = sample_java_service.to_dict()
        assert "id" in d
        assert "name" in d
        assert "entity_type" in d
        assert "language" in d
        assert "file_path" in d
        assert "line_number" in d
        assert "repo" in d
        assert "metadata" in d
        assert "confidence" in d

    def test_to_dict_serializes_enums_as_strings(
        self, sample_java_service: ServiceNode
    ) -> None:
        """to_dict() should serialize enum values as strings."""
        d = sample_java_service.to_dict()
        assert d["entity_type"] == "controller"
        assert d["language"] == "java"

    def test_default_confidence_is_one(self) -> None:
        """Default confidence should be 1.0."""
        entity = ServiceNode(
            id="test/java/service/TestService",
            name="TestService",
            entity_type=EntityType.SERVICE,
            language=Language.JAVA,
            file_path="TestService.java",
            line_number=1,
            repo="test-repo",
        )
        assert entity.confidence == 1.0


class TestServiceNode:
    """Tests for ServiceNode subclass."""

    def test_service_node_controller_type(
        self, sample_java_service: ServiceNode
    ) -> None:
        assert sample_java_service.entity_type == EntityType.CONTROLLER
        assert sample_java_service.language == Language.JAVA

    def test_service_node_base_path(
        self, sample_java_service: ServiceNode
    ) -> None:
        assert sample_java_service.base_path == "/api/coupons"


class TestEndpointNode:
    """Tests for EndpointNode subclass."""

    def test_endpoint_node_fields(self, sample_endpoint: EndpointNode) -> None:
        assert sample_endpoint.http_method == "GET"
        assert sample_endpoint.path == "/api/coupons/{userId}"
        assert sample_endpoint.is_consumer is False
        assert sample_endpoint.response_dto == "CouponResponseDto"

    def test_endpoint_node_entity_type(
        self, sample_endpoint: EndpointNode
    ) -> None:
        assert sample_endpoint.entity_type == EntityType.ENDPOINT


class TestModelNode:
    """Tests for ModelNode subclass."""

    def test_java_dto_is_response(self, sample_java_dto: ModelNode) -> None:
        assert sample_java_dto.is_response is True
        assert sample_java_dto.entity_type == EntityType.DTO
        assert sample_java_dto.language == Language.JAVA

    def test_dart_model_has_fields(self, sample_dart_model: ModelNode) -> None:
        assert len(sample_dart_model.fields) > 0
        field_names = [f["name"] for f in sample_dart_model.fields]
        assert "couponId" in field_names

    def test_typescript_interface_language(
        self, sample_typescript_interface: ModelNode
    ) -> None:
        assert sample_typescript_interface.language == Language.TYPESCRIPT


class TestCacheNode:
    """Tests for CacheNode subclass."""

    def test_cache_node_fields(self, sample_cache_node: CacheNode) -> None:
        assert sample_cache_node.cache_key_pattern == "feed:{userId}"
        assert sample_cache_node.ttl_seconds == 300
        assert sample_cache_node.operation == "read_write"
        assert sample_cache_node.cache_store == "redis"

    def test_cache_node_entity_type(self, sample_cache_node: CacheNode) -> None:
        assert sample_cache_node.entity_type == EntityType.CACHE


class TestMessageTopicNode:
    """Tests for MessageTopicNode subclass."""

    def test_kafka_topic_fields(self, sample_kafka_topic: MessageTopicNode) -> None:
        assert sample_kafka_topic.topic_name == "orders.placed"
        assert sample_kafka_topic.operation == "producer"
        assert sample_kafka_topic.message_schema == "OrderPlacedEvent"

    def test_kafka_topic_entity_type(
        self, sample_kafka_topic: MessageTopicNode
    ) -> None:
        assert sample_kafka_topic.entity_type == EntityType.MESSAGE_TOPIC


class TestDependencyEdge:
    """Tests for DependencyEdge."""

    def test_edge_to_dict(self) -> None:
        """to_dict() should serialize the edge correctly."""
        edge = DependencyEdge(
            id="edge-001",
            source_id="service-a",
            target_id="service-b",
            edge_type=EdgeType.CALLS,
            confidence=0.95,
        )
        d = edge.to_dict()
        assert d["id"] == "edge-001"
        assert d["source_id"] == "service-a"
        assert d["target_id"] == "service-b"
        assert d["edge_type"] == "CALLS"
        assert d["confidence"] == 0.95
        assert d["source_location"] is None

    def test_edge_with_source_location(self) -> None:
        """Edge with source_location should include it in to_dict()."""
        loc = SourceLocation(repo="my-repo", file_path="Service.java", line_number=10)
        edge = DependencyEdge(
            id="edge-002",
            source_id="src",
            target_id="tgt",
            edge_type=EdgeType.MAPS_TO,
            source_location=loc,
        )
        d = edge.to_dict()
        assert d["source_location"] is not None
        assert "my-repo" in d["source_location"]


class TestEnums:
    """Tests for Language, EntityType, EdgeType, ImpactSeverity enums."""

    def test_language_values(self) -> None:
        assert Language.JAVA.value == "java"
        assert Language.DART.value == "dart"
        assert Language.TYPESCRIPT.value == "typescript"

    def test_entity_type_values(self) -> None:
        assert EntityType.SERVICE.value == "service"
        assert EntityType.DTO.value == "dto"
        assert EntityType.CACHE.value == "cache"
        assert EntityType.MESSAGE_TOPIC.value == "message_topic"

    def test_edge_type_values(self) -> None:
        assert EdgeType.CALLS.value == "CALLS"
        assert EdgeType.MAPS_TO.value == "MAPS_TO"
        assert EdgeType.USES_CACHE.value == "USES_CACHE"

    def test_impact_severity_values(self) -> None:
        assert ImpactSeverity.BREAKING.value == "BREAKING"
        assert ImpactSeverity.ADDITIVE.value == "ADDITIVE"
        assert ImpactSeverity.INFORMATIONAL.value == "INFORMATIONAL"
