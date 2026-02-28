"""
Graph node and edge models for the Professor v10 architecture graph.

The architecture graph is the central data structure of the system. All parsing
output is normalized into these models, and all analysis operates on these models.

Design principles:
- All models are immutable (frozen Pydantic models where possible).
- All nodes carry a source_location for evidence linking.
- Edge types are explicit enums — no free-form strings for relationship semantics.
- IDs are deterministic: {repo}/{language}/{type}/{name} format enables deduplication.

See docs/design/03-dependency-modeling.md for full design rationale.
See docs/adr/002-graph-first-architecture.md for architectural decision.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class Language(StrEnum):
    """Programming language of the source entity."""

    JAVA = "java"
    DART = "dart"
    TYPESCRIPT = "typescript"
    UNKNOWN = "unknown"


class EntityType(StrEnum):
    """
    The architectural role of a code entity in the system.

    These types are language-agnostic — a SERVICE in Java and a SERVICE
    inferred from Dart are both EntityType.SERVICE, enabling cross-language
    impact analysis.
    """

    # Service-level entities
    SERVICE = "service"          # A deployable microservice
    CONTROLLER = "controller"    # REST controller / route handler
    COMPONENT = "component"      # Angular component (UI building block)

    # Data contract entities
    DTO = "dto"                  # Data Transfer Object (Java)
    MODEL = "model"              # Dart model / TypeScript interface (frontend)
    ENTITY = "entity"            # JPA database entity

    # API surface entities
    ENDPOINT = "endpoint"        # A specific HTTP endpoint (method + path)
    ROUTE = "route"              # A frontend navigation route

    # Infrastructure entities
    CACHE = "cache"              # A cache key/region
    DATABASE = "database"        # A database table or schema
    MESSAGE_TOPIC = "message_topic"   # A Kafka topic (or other message channel)
    EXTERNAL_INTEGRATION = "external_integration"  # Third-party API or service

    # Client entities
    FEIGN_CLIENT = "feign_client"    # Java Feign client (inter-service HTTP)
    HTTP_CLIENT = "http_client"      # Generic HTTP client call
    REPOSITORY = "repository"        # Database repository/DAO

    # Configuration entities
    FEATURE_FLAG = "feature_flag"    # Feature flag declaration
    CONFIG_PROPERTY = "config_property"  # Configuration property binding

    UNKNOWN = "unknown"


class EdgeType(StrEnum):
    """
    The semantic type of a dependency relationship between two entities.

    Edge types are the vocabulary of the architecture graph. They determine
    which edges are traversed during impact analysis for a given change type.

    See docs/design/03-dependency-modeling.md for layer-by-layer edge type description.
    """

    # Service communication edges
    CALLS = "CALLS"              # Synchronous call (REST/Feign/HTTP)
    DEPENDS_ON = "DEPENDS_ON"   # Generic structural dependency

    # Messaging edges (Kafka / message bus)
    PRODUCES = "PRODUCES"       # Service produces to a Kafka topic
    CONSUMES = "CONSUMES"       # Service consumes from a Kafka topic

    # Data persistence edges
    READS_DB = "READS_DB"       # Service/repo reads a database table
    WRITES_DB = "WRITES_DB"     # Service/repo writes a database table

    # Caching edges
    USES_CACHE = "USES_CACHE"   # Service reads/writes a cache key

    # Contract / schema edges
    MAPS_TO = "MAPS_TO"         # Java DTO maps to Dart model / TS interface
    RETURNS = "RETURNS"         # Endpoint returns a specific DTO/model
    ACCEPTS = "ACCEPTS"         # Endpoint accepts a specific request DTO

    # Structural edges
    EXPOSES = "EXPOSES"         # Controller exposes an endpoint
    IMPLEMENTS = "IMPLEMENTS"   # Service implements a contract/interface
    CONTAINS = "CONTAINS"       # Module/package contains a class


class ImpactSeverity(StrEnum):
    """
    Classification of impact severity for a change propagation result.

    Used in impact reports to communicate the urgency of each affected component.
    See docs/design/05-change-impact-propagation.md for classification rules.
    """

    BREAKING = "BREAKING"           # Consumer WILL break without code change
    ADDITIVE = "ADDITIVE"           # Consumer should be updated (optional field, etc.)
    TRANSPARENT = "TRANSPARENT"     # Internal change, no visible impact
    INFORMATIONAL = "INFORMATIONAL" # Awareness only, no action required


# ---------------------------------------------------------------------------
# Source Location — the evidence anchor for every entity
# ---------------------------------------------------------------------------


@dataclass
class SourceLocation:
    """
    Precise source code location for evidence linking.

    Every architectural claim in the output document must trace back to a
    SourceLocation. This enables human verification and satisfies the
    evidence-backed reasoning requirement (see docs/adr/005-evidence-backed-reasoning.md).
    """

    repo: str
    """Repository name (matches the repo name in the config)."""

    file_path: str
    """Relative or absolute path to the source file within the repository."""

    line_number: int = 0
    """1-based line number of the declaration. 0 means unknown."""

    commit_sha: str | None = None
    """Git commit SHA for point-in-time reproducibility (optional)."""

    def __str__(self) -> str:
        loc = f"{self.repo}/{self.file_path}:{self.line_number}"
        if self.commit_sha:
            loc += f"@{self.commit_sha[:8]}"
        return loc


# ---------------------------------------------------------------------------
# Base entity — every graph node inherits from this
# ---------------------------------------------------------------------------


@dataclass
class CodeEntity:
    """
    Base class for all architectural entities in the graph.

    Every node in the architecture graph is a CodeEntity subclass. This base
    class captures the minimal information common to all entities across all
    languages and layers.

    ID format: {repo}/{language}/{entity_type}/{name}
    Example: "coupon-engine/java/controller/CouponController"
    """

    id: str
    """Deterministic unique identifier. Used as the graph node key."""

    name: str
    """Human-readable entity name (class name, endpoint path, topic name, etc.)."""

    entity_type: EntityType
    """The architectural role of this entity."""

    language: Language
    """The programming language of the source file."""

    file_path: str
    """Path to the source file where this entity is declared."""

    line_number: int
    """1-based line number of the declaration."""

    repo: str
    """Name of the repository containing this entity."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """
    Language-specific or entity-type-specific additional data.

    Examples:
    - Java controller: {"annotation": "@RestController", "base_path": "/api/coupons"}
    - Kafka topic: {"operation": "producer", "topic_name": "orders.placed"}
    - Cache node: {"cache_key": "feed:{userId}", "ttl_seconds": 300}
    """

    confidence: float = 1.0
    """
    Confidence score for this entity's detection (0.0–1.0).

    Reflects how certain the parser is that this entity was correctly identified.
    Lower scores indicate detection via heuristics (naming convention) rather
    than explicit annotations.
    See docs/design/06-trust-validation.md for confidence scoring rules.
    """

    @property
    def source_location(self) -> SourceLocation:
        """Return a SourceLocation for evidence linking."""
        return SourceLocation(
            repo=self.repo,
            file_path=self.file_path,
            line_number=self.line_number,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict for JSON export."""
        return {
            "id": self.id,
            "name": self.name,
            "entity_type": self.entity_type.value,
            "language": self.language.value,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "repo": self.repo,
            "metadata": self.metadata,
            "confidence": self.confidence,
        }


# ---------------------------------------------------------------------------
# Concrete node types
# ---------------------------------------------------------------------------


@dataclass
class ServiceNode(CodeEntity):
    """
    Represents a deployable service, microservice, or major application module.

    Also used for controllers, repositories, and other service-level classes
    within a service (distinguished by entity_type).

    Examples:
    - A Spring Boot microservice (entity_type=SERVICE)
    - A @RestController class (entity_type=CONTROLLER)
    - A @Repository class (entity_type=REPOSITORY)
    - An Angular @Injectable service (entity_type=SERVICE)
    """

    base_path: str | None = None
    """For controllers: the @RequestMapping base path (e.g., '/api/coupons')."""

    port: int | None = None
    """For top-level services: the HTTP port if detectable from config."""


@dataclass
class EndpointNode(CodeEntity):
    """
    Represents a single HTTP API endpoint.

    Created from @GetMapping, @PostMapping, etc. in Java, or from
    HttpClient.get/post calls in Dart/TypeScript (where they represent
    the endpoint being consumed, not exposed).
    """

    http_method: str = "UNKNOWN"
    """HTTP method: GET, POST, PUT, DELETE, PATCH."""

    path: str = "/"
    """The endpoint path, e.g., '/api/coupons/{id}'."""

    request_dto: str | None = None
    """Name of the request DTO class/interface (if detectable)."""

    response_dto: str | None = None
    """Name of the response DTO class/interface (if detectable)."""

    is_consumer: bool = False
    """True if this endpoint is being consumed (Dart/TS HTTP call), False if exposed (Java controller)."""


@dataclass
class ModelNode(CodeEntity):
    """
    Represents a data model: Java DTO, Dart model class, or TypeScript interface.

    ModelNodes are the primary targets of cross-language schema alignment.
    A Java CouponResponseDto, a Dart CouponModel, and a TypeScript CouponDto
    are all ModelNodes that should be linked via MAPS_TO edges.

    See docs/design/02-cross-language-schema-alignment.md.
    """

    fields: list[dict[str, Any]] = field(default_factory=list)
    """
    List of field definitions extracted from the model.

    Each field dict contains: {"name": str, "type": str, "nullable": bool, "line": int}
    """

    is_request: bool = False
    """True if this model is used as a request body (input DTO)."""

    is_response: bool = False
    """True if this model is used as a response body (output DTO)."""


@dataclass
class CacheNode(CodeEntity):
    """
    Represents a cache key or cache region used by a service.

    Created from @Cacheable, @CacheEvict, RedisTemplate usage in Java,
    or from local storage patterns in Dart/TypeScript.
    """

    cache_key_pattern: str = ""
    """
    The cache key pattern, potentially with placeholders.
    Example: "feed:{userId}:{country}" or "coupon:{couponId}"
    """

    ttl_seconds: int | None = None
    """Time-to-live in seconds, if detectable from annotations or config."""

    operation: str = "read_write"
    """Operation type: 'read', 'write', 'evict', or 'read_write'."""

    cache_store: str = "redis"
    """Cache store type: 'redis', 'aerospike', 'local', 'memcached'."""


@dataclass
class DatabaseNode(CodeEntity):
    """
    Represents a database table, schema, or data store interaction.

    Created from @Entity/@Table annotations in Java (JPA), or from
    detected SQL queries and repository method patterns.
    """

    table_name: str | None = None
    """Database table name if detectable (from @Table(name="..."))."""

    schema_name: str | None = None
    """Database schema name if applicable."""

    operations: list[str] = field(default_factory=list)
    """Detected operations: ['SELECT', 'INSERT', 'UPDATE', 'DELETE']."""


@dataclass
class MessageTopicNode(CodeEntity):
    """
    Represents a Kafka topic (or other message channel) interaction.

    Created from @KafkaListener and KafkaTemplate.send() in Java.
    Represents the point of interaction, not the topic itself — the same
    topic will have separate producer and consumer nodes in different services.
    """

    topic_name: str = ""
    """
    The Kafka topic name. May contain placeholders like "${kafka.topics.orders}".
    """

    operation: str = "unknown"
    """'producer' if this service sends to the topic, 'consumer' if it receives."""

    consumer_group: str | None = None
    """Kafka consumer group ID (for consumer nodes)."""

    message_schema: str | None = None
    """Name of the message payload class/type, if detectable."""


@dataclass
class ExternalIntegrationNode(CodeEntity):
    """
    Represents a dependency on an external third-party service or API.

    Examples: payment gateway, SMS provider, push notification service,
    third-party analytics, geocoding API.
    """

    base_url: str | None = None
    """The external service base URL, if detectable."""

    integration_type: str = "http"
    """Integration mechanism: 'http', 'sdk', 'grpc', 'webhook'."""


# ---------------------------------------------------------------------------
# Edge model
# ---------------------------------------------------------------------------


@dataclass
class DependencyEdge:
    """
    Represents a directed dependency relationship between two architectural entities.

    Edges are the relationships in the architecture graph. The edge_type determines
    the semantic meaning of the relationship, which in turn determines which edges
    are traversed during impact analysis for a given change type.

    See docs/design/03-dependency-modeling.md for edge type semantics.
    """

    id: str
    """Deterministic unique identifier for this edge: {source_id}→{edge_type}→{target_id}."""

    source_id: str
    """ID of the source node (the entity that has the dependency)."""

    target_id: str
    """ID of the target node (the entity being depended upon)."""

    edge_type: EdgeType
    """The semantic type of this dependency relationship."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """
    Additional context about the relationship.

    Examples:
    - CALLS edge: {"http_method": "GET", "endpoint_path": "/api/coupons/{id}"}
    - USES_CACHE edge: {"cache_key": "feed:{userId}", "operation": "read"}
    - MAPS_TO edge: {"field_mapping": {"estimatedSavings": "estimatedSavings"}}
    """

    source_location: SourceLocation | None = None
    """Where in the code this dependency is declared (for evidence linking)."""

    confidence: float = 1.0
    """Confidence score for this edge's detection accuracy (0.0–1.0)."""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict for JSON export."""
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "edge_type": self.edge_type.value,
            "metadata": self.metadata,
            "source_location": str(self.source_location) if self.source_location else None,
            "confidence": self.confidence,
        }
