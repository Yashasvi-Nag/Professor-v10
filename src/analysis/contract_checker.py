"""
Contract validation for Professor v10.

Validates the consistency of API contracts across service boundaries:
- Detects mismatched DTOs between services (field drift)
- Finds orphan endpoints (declared but never called)
- Validates Feign client → Controller alignment
- Checks frontend model consistency with backend DTOs
- Detects broken Kafka producer→consumer chains

Contract validation runs after graph construction and produces a list of
ContractViolation objects. These violations are included in the output document
as warnings and drive human-review checkpoints.

See docs/design/06-trust-validation.md for the full validation rule set.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from src.graph.models import (
    CodeEntity,
)
from src.graph.store import GraphStore


class ViolationSeverity(StrEnum):
    """Severity of a contract validation violation."""

    HIGH = "HIGH"       # Likely to cause a production issue
    MEDIUM = "MEDIUM"   # Architectural smell, should be resolved
    LOW = "LOW"         # Informational, consider addressing


@dataclass
class ContractViolation:
    """
    A detected contract inconsistency in the architecture graph.

    Each violation represents a specific rule that has been violated,
    with evidence pointing to the relevant code artifacts.
    """

    rule_id: str
    """The validation rule that was violated (e.g., 'VR-001')."""

    severity: ViolationSeverity
    """How serious this violation is."""

    description: str
    """Human-readable description of the violation."""

    affected_entities: list[CodeEntity] = field(default_factory=list)
    """The code entities involved in the violation."""

    recommendation: str = ""
    """Recommended remediation action."""

    evidence_links: list[str] = field(default_factory=list)
    """Source location strings pointing to the code artifacts involved."""


@dataclass
class ContractCheckResult:
    """
    The complete result of running all contract validation checks.
    """

    violations: list[ContractViolation] = field(default_factory=list)
    """All detected contract violations."""

    checks_run: int = 0
    """Total number of validation rules executed."""

    @property
    def high_severity(self) -> list[ContractViolation]:
        """Return HIGH severity violations only."""
        return [v for v in self.violations if v.severity == ViolationSeverity.HIGH]

    @property
    def medium_severity(self) -> list[ContractViolation]:
        """Return MEDIUM severity violations only."""
        return [v for v in self.violations if v.severity == ViolationSeverity.MEDIUM]

    @property
    def is_clean(self) -> bool:
        """Return True if no violations were found."""
        return len(self.violations) == 0


class ContractChecker:
    """
    Validates API contracts and architectural consistency across the graph.

    Runs a battery of validation rules against the architecture graph and
    returns a ContractCheckResult with all detected violations.

    Usage:
        checker = ContractChecker(graph_store)
        result = checker.check_all()
        for violation in result.high_severity:
            print(f"[{violation.rule_id}] {violation.description}")
    """

    def __init__(self, store: GraphStore) -> None:
        """
        Initialize the contract checker with a populated graph store.

        Args:
            store: The architecture graph store to validate.
        """
        self._store = store

    def check_all(self) -> ContractCheckResult:
        """
        Run all contract validation rules against the graph.

        Executes each validation rule in sequence and aggregates results.
        Rules are independent — a failure in one does not prevent others from running.

        Returns:
            ContractCheckResult with all violations and statistics.
        """
        result = ContractCheckResult()

        # Run each validation rule and collect violations
        checks = [
            self._check_feign_clients_have_controllers,       # VR-001
            self._check_kafka_producers_have_consumers,        # VR-002
            self._check_api_endpoints_have_model_mappings,     # VR-003
            self._check_cache_annotations_are_resolvable,      # VR-004
            self._check_no_circular_service_dependencies,      # VR-005
            self._check_all_impact_claims_have_evidence,       # VR-006
            self._check_orphan_nodes,                          # VR-007 (informational)
            self._check_cross_language_dto_alignment,          # VR-008
        ]

        for check in checks:
            violations = check()
            result.violations.extend(violations)
            result.checks_run += 1

        return result

    # -------------------------------------------------------------------------
    # Validation rules
    # -------------------------------------------------------------------------

    def _check_feign_clients_have_controllers(self) -> list[ContractViolation]:
        """
        VR-001: Every @FeignClient must have a corresponding @RestController.

        If a Feign client is calling a service that has no corresponding controller
        in the graph, it means either:
        a) The target service was not included in the parse scope
        b) The endpoint path does not match any known controller
        c) The Feign client has an incorrect target URL

        This is a HIGH severity violation because the call will fail at runtime
        if the endpoint does not exist.
        """
        violations = []

        # TODO: Implement VR-001 validation
        # Algorithm:
        # 1. Find all nodes with entity_type=FEIGN_CLIENT
        # 2. For each Feign client, find its corresponding CALLS edge
        # 3. Follow the CALLS edge to the target endpoint/controller
        # 4. If no target found → ContractViolation(rule_id="VR-001", severity=HIGH)
        # 5. Include the Feign client file path as evidence link
        # 6. Recommendation: "Verify target service is included in parse scope
        #    or check Feign client URL configuration"

        return violations

    def _check_kafka_producers_have_consumers(self) -> list[ContractViolation]:
        """
        VR-002: Every Kafka producer topic should have at least one consumer.

        A topic with producers but no consumers is either:
        a) A "fire and forget" topic where consumers are out of parse scope
        b) Dead code (topic is produced but never consumed — architectural waste)
        c) A future-use topic not yet connected to a consumer

        This is MEDIUM severity — the system still functions, but architectural
        completeness is suspect.
        """
        violations = []

        # TODO: Implement VR-002 validation
        # Algorithm:
        # 1. Find all MessageTopicNode with operation="producer"
        # 2. For each producer topic_name, find corresponding consumer MessageTopicNodes
        # 3. If no consumers found for a topic → ContractViolation(rule_id="VR-002", severity=MEDIUM)
        # 4. Recommendation: "Verify consumer exists and is included in parse scope"

        return violations

    def _check_api_endpoints_have_model_mappings(self) -> list[ContractViolation]:
        """
        VR-003: Every API endpoint DTO should have a frontend model mapping.

        If a Java DTO used in a REST response has no corresponding Dart or TypeScript
        model, it indicates either:
        a) The frontend repos were not included in the parse scope
        b) The frontend uses raw JSON without a typed model (anti-pattern)
        c) The endpoint is internal-only (service-to-service, no frontend consumer)

        This is MEDIUM severity.
        """
        violations = []

        # TODO: Implement VR-003 validation
        # Algorithm:
        # 1. Find all EndpointNode with a response_dto set (is_consumer=False)
        # 2. For each response DTO, check if there is a MAPS_TO edge
        #    connecting it to a Dart or TypeScript ModelNode
        # 3. If no MAPS_TO edge found → ContractViolation(rule_id="VR-003", severity=MEDIUM)
        # 4. Note: if all repos are Java-only, this check should be skipped

        return violations

    def _check_cache_annotations_are_resolvable(self) -> list[ContractViolation]:
        """
        VR-004: Every @Cacheable key should be traceable to a CacheNode in the graph.

        If a service uses @Cacheable but no CacheNode was created for it,
        the parser failed to extract the cache key pattern.

        This is LOW severity (parser completeness check).
        """
        violations = []

        # TODO: Implement VR-004 validation
        # Algorithm:
        # 1. Find all ServiceNodes with USES_CACHE edges
        # 2. Verify each USES_CACHE edge target is a CacheNode with a non-empty key pattern
        # 3. If cache_key_pattern is empty → ContractViolation(rule_id="VR-004", severity=LOW)

        return violations

    def _check_no_circular_service_dependencies(self) -> list[ContractViolation]:
        """
        VR-005: No circular service-to-service dependencies (A→B→C→A).

        Circular dependencies indicate an architectural anti-pattern. They
        make it impossible to determine deployment order and create potential
        for cascading failures.

        This is HIGH severity.
        """
        violations = []

        # TODO: Implement VR-005 validation using networkx cycle detection
        # Algorithm:
        # 1. Extract subgraph containing only SERVICE and CONTROLLER nodes
        #    with CALLS edges between them
        # 2. Use networkx.find_cycle() to detect cycles
        # 3. For each cycle found → ContractViolation(rule_id="VR-005", severity=HIGH)
        #    Include the cycle path as evidence
        # 4. Recommendation: "Break circular dependency by introducing an interface
        #    or event-driven communication"

        return violations

    def _check_all_impact_claims_have_evidence(self) -> list[ContractViolation]:
        """
        VR-006: Every edge in the graph must have a source location (evidence link).

        Edges without source locations cannot be traced to specific code,
        violating the evidence-backed reasoning requirement.

        This is HIGH severity (trust violation).
        """
        violations = []

        for edge in self._store.all_edges():
            if edge.source_location is None:
                # Find the source and target entities for context
                source_entity = self._store.get_node(edge.source_id)
                target_entity = self._store.get_node(edge.target_id)

                affected = [e for e in [source_entity, target_entity] if e is not None]

                violations.append(
                    ContractViolation(
                        rule_id="VR-006",
                        severity=ViolationSeverity.HIGH,
                        description=(
                            f"Edge '{edge.edge_type.value}' from '{edge.source_id}' "
                            f"to '{edge.target_id}' has no source location evidence."
                        ),
                        affected_entities=affected,
                        recommendation=(
                            "Ensure the parser that created this edge populates "
                            "the source_location field with file path and line number."
                        ),
                    )
                )

        return violations

    def _check_orphan_nodes(self) -> list[ContractViolation]:
        """
        VR-007: Nodes with no edges are potential parsing gaps.

        An orphan node (no incoming or outgoing edges) typically means:
        a) The entity was detected but its relationships were not resolved
        b) A dead code class with no usage

        This is LOW severity (informational).
        """
        violations = []

        # TODO: Implement VR-007 orphan detection
        # Algorithm:
        # 1. For each node in the graph, check if it has any edges (in or out)
        # 2. Exclude nodes that are expected to be isolated (e.g., standalone config classes)
        # 3. For each truly orphan node → ContractViolation(rule_id="VR-007", severity=LOW)
        # 4. Recommendation: "Verify this entity has relationships or remove from parse scope"

        return violations

    def _check_cross_language_dto_alignment(self) -> list[ContractViolation]:
        """
        VR-008: Java DTOs used in API responses should have aligned frontend models.

        For each Java DTO that appears in an API response, check that the
        corresponding Dart/TypeScript models have the same fields. Field drift
        (fields present in Java but missing in Dart/TS) is flagged as a violation.

        This is MEDIUM severity — the app may work but receives unexpected data.
        """
        violations = []

        # TODO: Implement VR-008 cross-language DTO field alignment check
        # Algorithm:
        # 1. Find all Java ModelNodes (DTOs)
        # 2. For each Java DTO, find all MAPS_TO edges pointing to Dart/TS models
        # 3. Compare the field lists: java_dto.fields vs dart_model.fields vs ts_interface.fields
        # 4. For each field in Java DTO that is missing from a Dart/TS model:
        #    → ContractViolation(rule_id="VR-008", severity=MEDIUM)
        #    with description: "Field 'X' present in Java DTO but missing in Dart model"
        # 5. Include source locations of both the Java and Dart/TS files as evidence

        return violations
