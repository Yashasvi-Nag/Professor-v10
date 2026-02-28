"""
Shared pytest fixtures for Professor v10 tests.

Provides reusable test data including:
- Sample graph stores with pre-populated nodes and edges
- Sample CodeEntity objects for each language/type
- Sample FeatureRequest and StructuredPRD objects
- Sample ImpactReport for document generation tests

Using these fixtures ensures tests are consistent and maintainable.
"""

import pytest

from src.graph.models import (
    CacheNode,
    DependencyEdge,
    EdgeType,
    EndpointNode,
    EntityType,
    Language,
    MessageTopicNode,
    ModelNode,
    ServiceNode,
    SourceLocation,
)
from src.graph.store import InMemoryGraphStore
from src.prd.models import (
    AffectedComponent,
    ComponentRole,
    ConstraintSource,
    FeatureRequest,
    QuestionType,
    StructuredPRD,
    TechnicalConstraint,
)

# ---------------------------------------------------------------------------
# Graph node fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_java_service() -> ServiceNode:
    """A sample Java Spring Boot controller node."""
    return ServiceNode(
        id="coupon-engine/java/controller/CouponController",
        name="CouponController",
        entity_type=EntityType.CONTROLLER,
        language=Language.JAVA,
        file_path="src/main/java/controller/CouponController.java",
        line_number=12,
        repo="coupon-engine",
        metadata={"annotation": "@RestController", "base_path": "/api/coupons"},
        base_path="/api/coupons",
    )


@pytest.fixture
def sample_java_dto() -> ModelNode:
    """A sample Java DTO (CouponResponseDto)."""
    return ModelNode(
        id="coupon-engine/java/dto/CouponResponseDto",
        name="CouponResponseDto",
        entity_type=EntityType.DTO,
        language=Language.JAVA,
        file_path="src/main/java/dto/CouponResponseDto.java",
        line_number=5,
        repo="coupon-engine",
        fields=[
            {"name": "couponId", "type": "String", "nullable": False, "line": 7},
            {"name": "discountAmount", "type": "BigDecimal", "nullable": False, "line": 9},
        ],
        is_response=True,
    )


@pytest.fixture
def sample_endpoint() -> EndpointNode:
    """A sample REST API endpoint node."""
    return EndpointNode(
        id="coupon-engine/java/endpoint/GET_/api/coupons/{userId}",
        name="/api/coupons/{userId}",
        entity_type=EntityType.ENDPOINT,
        language=Language.JAVA,
        file_path="src/main/java/controller/CouponController.java",
        line_number=25,
        repo="coupon-engine",
        http_method="GET",
        path="/api/coupons/{userId}",
        response_dto="CouponResponseDto",
        is_consumer=False,
    )


@pytest.fixture
def sample_dart_model() -> ModelNode:
    """A sample Dart Flutter model node that maps to the Java DTO."""
    return ModelNode(
        id="flutter-app/dart/model/CouponModel",
        name="CouponModel",
        entity_type=EntityType.MODEL,
        language=Language.DART,
        file_path="lib/models/coupon_model.dart",
        line_number=3,
        repo="flutter-app",
        fields=[
            {"name": "couponId", "type": "String", "nullable": False, "line": 5},
            {"name": "discountAmount", "type": "double", "nullable": False, "line": 6},
        ],
        is_response=True,
    )


@pytest.fixture
def sample_typescript_interface() -> ModelNode:
    """A sample TypeScript interface node that maps to the Java DTO."""
    return ModelNode(
        id="angular-admin/typescript/interface/CouponDto",
        name="CouponDto",
        entity_type=EntityType.MODEL,
        language=Language.TYPESCRIPT,
        file_path="src/app/models/coupon.dto.ts",
        line_number=1,
        repo="angular-admin",
        fields=[
            {"name": "couponId", "type": "string", "nullable": False, "line": 2},
            {"name": "discountAmount", "type": "number", "nullable": False, "line": 3},
        ],
        is_response=True,
    )


@pytest.fixture
def sample_cache_node() -> CacheNode:
    """A sample Redis cache node."""
    return CacheNode(
        id="feed-service/java/cache/feed:{userId}",
        name="feed-cache",
        entity_type=EntityType.CACHE,
        language=Language.JAVA,
        file_path="src/main/java/service/FeedService.java",
        line_number=45,
        repo="feed-service",
        cache_key_pattern="feed:{userId}",
        ttl_seconds=300,
        operation="read_write",
        cache_store="redis",
    )


@pytest.fixture
def sample_kafka_topic() -> MessageTopicNode:
    """A sample Kafka topic node (producer)."""
    return MessageTopicNode(
        id="order-service/java/topic/orders.placed",
        name="orders-placed-producer",
        entity_type=EntityType.MESSAGE_TOPIC,
        language=Language.JAVA,
        file_path="src/main/java/events/OrderEventProducer.java",
        line_number=30,
        repo="order-service",
        topic_name="orders.placed",
        operation="producer",
        message_schema="OrderPlacedEvent",
    )


@pytest.fixture
def sample_feed_service() -> ServiceNode:
    """A sample feed-service node."""
    return ServiceNode(
        id="feed-service/java/service/FeedService",
        name="FeedService",
        entity_type=EntityType.SERVICE,
        language=Language.JAVA,
        file_path="src/main/java/service/FeedService.java",
        line_number=10,
        repo="feed-service",
    )


# ---------------------------------------------------------------------------
# Graph store fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_graph_store(
    sample_java_service,
    sample_java_dto,
    sample_endpoint,
    sample_dart_model,
    sample_typescript_interface,
    sample_cache_node,
    sample_feed_service,
) -> InMemoryGraphStore:
    """
    A fully populated InMemoryGraphStore for use in query and analysis tests.

    Graph topology:
    CouponController --EXPOSES--> GET /api/coupons/{userId}
    GET /api/coupons/{userId} --RETURNS--> CouponResponseDto
    CouponResponseDto --MAPS_TO--> CouponModel (Dart)
    CouponResponseDto --MAPS_TO--> CouponDto (TypeScript)
    FeedService --CALLS--> CouponController
    FeedService --USES_CACHE--> feed:{userId}
    """
    store = InMemoryGraphStore()

    # Add nodes
    store.add_node(sample_java_service)
    store.add_node(sample_java_dto)
    store.add_node(sample_endpoint)
    store.add_node(sample_dart_model)
    store.add_node(sample_typescript_interface)
    store.add_node(sample_cache_node)
    store.add_node(sample_feed_service)

    # Add edges
    store.add_edge(DependencyEdge(
        id="edge-001",
        source_id=sample_java_service.id,
        target_id=sample_endpoint.id,
        edge_type=EdgeType.EXPOSES,
        source_location=SourceLocation(
            repo="coupon-engine",
            file_path="src/main/java/controller/CouponController.java",
            line_number=25,
        ),
    ))

    store.add_edge(DependencyEdge(
        id="edge-002",
        source_id=sample_endpoint.id,
        target_id=sample_java_dto.id,
        edge_type=EdgeType.RETURNS,
        source_location=SourceLocation(
            repo="coupon-engine",
            file_path="src/main/java/controller/CouponController.java",
            line_number=25,
        ),
    ))

    store.add_edge(DependencyEdge(
        id="edge-003",
        source_id=sample_java_dto.id,
        target_id=sample_dart_model.id,
        edge_type=EdgeType.MAPS_TO,
        source_location=SourceLocation(
            repo="coupon-engine",
            file_path="src/main/java/dto/CouponResponseDto.java",
            line_number=5,
        ),
        confidence=0.90,
    ))

    store.add_edge(DependencyEdge(
        id="edge-004",
        source_id=sample_java_dto.id,
        target_id=sample_typescript_interface.id,
        edge_type=EdgeType.MAPS_TO,
        source_location=SourceLocation(
            repo="coupon-engine",
            file_path="src/main/java/dto/CouponResponseDto.java",
            line_number=5,
        ),
        confidence=0.85,
    ))

    store.add_edge(DependencyEdge(
        id="edge-005",
        source_id=sample_feed_service.id,
        target_id=sample_java_service.id,
        edge_type=EdgeType.CALLS,
        source_location=SourceLocation(
            repo="feed-service",
            file_path="src/main/java/clients/CouponEngineClient.java",
            line_number=18,
        ),
    ))

    store.add_edge(DependencyEdge(
        id="edge-006",
        source_id=sample_feed_service.id,
        target_id=sample_cache_node.id,
        edge_type=EdgeType.USES_CACHE,
        source_location=SourceLocation(
            repo="feed-service",
            file_path="src/main/java/service/FeedService.java",
            line_number=45,
        ),
    ))

    return store


# ---------------------------------------------------------------------------
# PRD fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_feature_request() -> FeatureRequest:
    """A sample feature request for the 'add estimatedSavings to feed' scenario."""
    return FeatureRequest(
        title="Add estimated savings to coupon feed",
        description=(
            "Add the estimatedSavings field to the CouponResponseDto so that "
            "the feed shows how much users will save. Apply to Indian users only."
        ),
        requester="Product Manager - Coupons",
        priority="high",
        known_constraints=["India only", "Must be backward compatible"],
    )


@pytest.fixture
def sample_structured_prd(sample_feature_request) -> StructuredPRD:
    """A sample finalized StructuredPRD for document generation tests."""
    return StructuredPRD(
        feature_id="FEAT-TEST01",
        title=sample_feature_request.title,
        original_request=sample_feature_request,
        technical_constraints=[
            TechnicalConstraint(
                constraint_type=QuestionType.SCOPE,
                description="SCOPE: India (country=IN) only",
                source=ConstraintSource.CLARIFICATION_ANSWER,
            ),
            TechnicalConstraint(
                constraint_type=QuestionType.BACKWARD_COMPAT,
                description="BACKWARD_COMPAT: Field is nullable; old clients receive null",
                source=ConstraintSource.CLARIFICATION_ANSWER,
            ),
            TechnicalConstraint(
                constraint_type=QuestionType.CACHING,
                description="CACHING: Include in cache; no key change required",
                source=ConstraintSource.CLARIFICATION_ANSWER,
            ),
        ],
        affected_components=[
            AffectedComponent(
                node_id="coupon-engine/java/dto/CouponResponseDto",
                name="CouponResponseDto",
                component_type="dto",
                repo="coupon-engine",
                language="java",
                role=ComponentRole.OWNS_CONTRACT,
                reason="Directly contains the field being added",
                confidence=0.95,
            ),
        ],
        completeness_score=0.92,
        is_finalized=True,
    )
