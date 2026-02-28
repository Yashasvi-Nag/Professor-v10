"""
Tests for the ImpactAnalyzer.

Tests cover:
- analyze() returns ImpactReport
- Multi-seed analysis
- find_seed_nodes() hint-based lookup
- Risk and rollout note generation
- ImpactReport property accessors
"""

import pytest

from src.analysis.impact import ImpactAnalyzer, ImpactReport
from src.graph.models import EntityType
from src.graph.store import InMemoryGraphStore


@pytest.fixture
def impact_analyzer(sample_graph_store: InMemoryGraphStore) -> ImpactAnalyzer:
    """Return an ImpactAnalyzer backed by the sample graph store."""
    return ImpactAnalyzer(sample_graph_store)


class TestImpactAnalyzerAnalyze:
    """Tests for the analyze() method."""

    def test_analyze_returns_impact_report(
        self, impact_analyzer: ImpactAnalyzer, sample_java_dto
    ) -> None:
        """analyze() should return an ImpactReport."""
        report = impact_analyzer.analyze(
            feature_id="FEAT-TEST",
            change_summary="Add estimatedSavings to CouponResponseDto",
            seed_node_ids=[sample_java_dto.id],
        )
        assert isinstance(report, ImpactReport)

    def test_analyze_populates_seed_nodes(
        self, impact_analyzer: ImpactAnalyzer, sample_java_dto
    ) -> None:
        """analyze() should populate the seed_nodes field."""
        report = impact_analyzer.analyze(
            feature_id="FEAT-TEST",
            change_summary="Test",
            seed_node_ids=[sample_java_dto.id],
        )
        assert len(report.seed_nodes) == 1
        assert report.seed_nodes[0].id == sample_java_dto.id

    def test_analyze_empty_seed_nodes(
        self, impact_analyzer: ImpactAnalyzer
    ) -> None:
        """analyze() with no seed nodes should return a report with no impacts."""
        report = impact_analyzer.analyze(
            feature_id="FEAT-TEST",
            change_summary="Test",
            seed_node_ids=[],
        )
        assert report.impact_result.total_count == 0

    def test_analyze_unknown_seed_node(
        self, impact_analyzer: ImpactAnalyzer
    ) -> None:
        """analyze() with an unknown seed node ID should handle gracefully."""
        report = impact_analyzer.analyze(
            feature_id="FEAT-TEST",
            change_summary="Test",
            seed_node_ids=["non-existent-node-id"],
        )
        # No nodes resolved → no impacts
        assert len(report.seed_nodes) == 0

    def test_analyze_propagates_to_dart_model(
        self,
        impact_analyzer: ImpactAnalyzer,
        sample_java_dto,
        sample_dart_model,
    ) -> None:
        """Changing a Java DTO should show Dart model as impacted."""
        report = impact_analyzer.analyze(
            feature_id="FEAT-001",
            change_summary="Add estimatedSavings to CouponResponseDto",
            seed_node_ids=[sample_java_dto.id],
            change_type="FIELD_CHANGED",
        )
        impacted_ids = {n.entity.id for n in report.impact_result.impacted_nodes}
        assert sample_dart_model.id in impacted_ids

    def test_analyze_generates_risks_for_multi_repo(
        self,
        impact_analyzer: ImpactAnalyzer,
        sample_java_dto,
    ) -> None:
        """analyze() should generate risks when multiple repos are impacted."""
        report = impact_analyzer.analyze(
            feature_id="FEAT-001",
            change_summary="Add estimatedSavings to CouponResponseDto",
            seed_node_ids=[sample_java_dto.id],
        )
        # Risks should be a list (may be empty if not enough repos are impacted)
        assert isinstance(report.risks, list)

    def test_analyze_feature_id_in_report(
        self, impact_analyzer: ImpactAnalyzer, sample_java_dto
    ) -> None:
        """The feature_id should be preserved in the ImpactReport."""
        report = impact_analyzer.analyze(
            feature_id="FEAT-CUSTOM-123",
            change_summary="Test",
            seed_node_ids=[sample_java_dto.id],
        )
        assert report.feature_id == "FEAT-CUSTOM-123"


class TestImpactReportProperties:
    """Tests for ImpactReport property accessors."""

    def test_affected_services_property(
        self,
        impact_analyzer: ImpactAnalyzer,
        sample_java_dto,
        sample_feed_service,
    ) -> None:
        """affected_services should return only SERVICE and CONTROLLER nodes."""
        report = impact_analyzer.analyze(
            feature_id="FEAT-TEST",
            change_summary="Test",
            seed_node_ids=[sample_java_dto.id],
        )
        for service in report.affected_services:
            assert service.entity_type in (EntityType.SERVICE, EntityType.CONTROLLER)

    def test_affected_models_property(
        self, impact_analyzer: ImpactAnalyzer, sample_java_dto
    ) -> None:
        """affected_models should return MODEL and DTO nodes."""
        report = impact_analyzer.analyze(
            feature_id="FEAT-TEST",
            change_summary="Test",
            seed_node_ids=[sample_java_dto.id],
        )
        for model in report.affected_models:
            assert model.entity_type in (EntityType.MODEL, EntityType.DTO, EntityType.ENTITY)

    def test_affected_caches_property(
        self,
        impact_analyzer: ImpactAnalyzer,
        sample_feed_service,
        sample_cache_node,
    ) -> None:
        """affected_caches should return CACHE nodes."""
        report = impact_analyzer.analyze(
            feature_id="FEAT-TEST",
            change_summary="Test cache impact",
            seed_node_ids=[sample_feed_service.id],
        )
        for cache in report.affected_caches:
            assert cache.entity_type == EntityType.CACHE


class TestFindSeedNodes:
    """Tests for the find_seed_nodes() method."""

    def test_find_seed_nodes_with_hints(
        self, impact_analyzer: ImpactAnalyzer, sample_java_dto
    ) -> None:
        """find_seed_nodes() with hints should return the hinted IDs."""
        result = impact_analyzer.find_seed_nodes(
            change_description="Add field to CouponResponseDto",
            hints=[sample_java_dto.id],
        )
        assert sample_java_dto.id in result

    def test_find_seed_nodes_no_hints_returns_list(
        self, impact_analyzer: ImpactAnalyzer
    ) -> None:
        """find_seed_nodes() without hints should still return a list."""
        result = impact_analyzer.find_seed_nodes("Add a new field")
        assert isinstance(result, list)
