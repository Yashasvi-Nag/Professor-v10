"""
Tests for the ContractChecker.

Tests cover:
- check_all() runs without error
- ContractCheckResult structure
- VR-006 edge evidence check
- Clean graph produces no violations
"""

import pytest

from src.analysis.contract_checker import (
    ContractChecker,
    ContractCheckResult,
    ViolationSeverity,
)
from src.graph.models import DependencyEdge, EdgeType, SourceLocation
from src.graph.store import InMemoryGraphStore


@pytest.fixture
def contract_checker(sample_graph_store: InMemoryGraphStore) -> ContractChecker:
    """Return a ContractChecker backed by the sample graph store."""
    return ContractChecker(sample_graph_store)


class TestContractCheckerCheckAll:
    """Tests for the check_all() method."""

    def test_check_all_returns_result(
        self, contract_checker: ContractChecker
    ) -> None:
        """check_all() should return a ContractCheckResult."""
        result = contract_checker.check_all()
        assert isinstance(result, ContractCheckResult)

    def test_check_all_runs_all_checks(
        self, contract_checker: ContractChecker
    ) -> None:
        """check_all() should run all registered checks."""
        result = contract_checker.check_all()
        # At least 8 checks are registered
        assert result.checks_run >= 8

    def test_check_all_violations_are_list(
        self, contract_checker: ContractChecker
    ) -> None:
        """violations should be a list."""
        result = contract_checker.check_all()
        assert isinstance(result.violations, list)

    def test_result_severity_properties(
        self, contract_checker: ContractChecker
    ) -> None:
        """high_severity and medium_severity properties should work."""
        result = contract_checker.check_all()
        for v in result.high_severity:
            assert v.severity == ViolationSeverity.HIGH
        for v in result.medium_severity:
            assert v.severity == ViolationSeverity.MEDIUM


class TestContractCheckerEvidenceRule:
    """Tests for VR-006 — edges must have source locations."""

    def test_edges_without_evidence_are_flagged(self) -> None:
        """An edge with no source_location should trigger VR-006."""
        from src.graph.models import EntityType, Language, ServiceNode

        store = InMemoryGraphStore()
        node_a = ServiceNode(
            id="repo/java/service/ServiceA",
            name="ServiceA",
            entity_type=EntityType.SERVICE,
            language=Language.JAVA,
            file_path="ServiceA.java",
            line_number=1,
            repo="repo",
        )
        node_b = ServiceNode(
            id="repo/java/service/ServiceB",
            name="ServiceB",
            entity_type=EntityType.SERVICE,
            language=Language.JAVA,
            file_path="ServiceB.java",
            line_number=1,
            repo="repo",
        )
        store.add_node(node_a)
        store.add_node(node_b)

        # Add edge WITHOUT source_location
        edge = DependencyEdge(
            id="edge-no-evidence",
            source_id=node_a.id,
            target_id=node_b.id,
            edge_type=EdgeType.CALLS,
            source_location=None,  # No evidence!
        )
        store.add_edge(edge)

        checker = ContractChecker(store)
        result = checker.check_all()

        vr006_violations = [v for v in result.violations if v.rule_id == "VR-006"]
        assert len(vr006_violations) >= 1

    def test_edges_with_evidence_do_not_trigger_vr006(self) -> None:
        """An edge with a source_location should NOT trigger VR-006."""
        from src.graph.models import EntityType, Language, ServiceNode

        store = InMemoryGraphStore()
        node_a = ServiceNode(
            id="repo/java/service/ServiceA",
            name="ServiceA",
            entity_type=EntityType.SERVICE,
            language=Language.JAVA,
            file_path="ServiceA.java",
            line_number=1,
            repo="repo",
        )
        node_b = ServiceNode(
            id="repo/java/service/ServiceB",
            name="ServiceB",
            entity_type=EntityType.SERVICE,
            language=Language.JAVA,
            file_path="ServiceB.java",
            line_number=1,
            repo="repo",
        )
        store.add_node(node_a)
        store.add_node(node_b)

        # Add edge WITH source_location
        edge = DependencyEdge(
            id="edge-with-evidence",
            source_id=node_a.id,
            target_id=node_b.id,
            edge_type=EdgeType.CALLS,
            source_location=SourceLocation(
                repo="repo", file_path="ServiceA.java", line_number=10
            ),
        )
        store.add_edge(edge)

        checker = ContractChecker(store)
        result = checker.check_all()

        vr006_violations = [v for v in result.violations if v.rule_id == "VR-006"]
        assert len(vr006_violations) == 0


class TestContractCheckResult:
    """Tests for ContractCheckResult properties."""

    def test_is_clean_when_no_violations(self) -> None:
        """is_clean should return True when there are no violations."""
        result = ContractCheckResult(violations=[], checks_run=5)
        assert result.is_clean is True

    def test_is_not_clean_when_violations_exist(self) -> None:
        """is_clean should return False when violations exist."""
        from src.analysis.contract_checker import ContractViolation
        violation = ContractViolation(
            rule_id="VR-001",
            severity=ViolationSeverity.HIGH,
            description="Test violation",
        )
        result = ContractCheckResult(violations=[violation], checks_run=1)
        assert result.is_clean is False
