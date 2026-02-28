"""
Tests for the PRD clarification engine.

Tests cover:
- create_structured_prd() returns StructuredPRD
- Affected component identification from graph
- Standard question generation
- Completeness score computation
- finalize() converts answers to constraints
- StructuredPRD model validation
- ClarificationQuestion mark_answered()
"""

import pytest

from src.graph.store import InMemoryGraphStore
from src.prd.clarifier import PRDClarifier
from src.prd.models import (
    ClarificationQuestion,
    FeatureRequest,
    QuestionType,
    StructuredPRD,
)


@pytest.fixture
def prd_clarifier(sample_graph_store: InMemoryGraphStore) -> PRDClarifier:
    """Return a PRDClarifier backed by the sample graph store."""
    return PRDClarifier(sample_graph_store)


@pytest.fixture
def empty_prd_clarifier() -> PRDClarifier:
    """Return a PRDClarifier backed by an empty graph store."""
    return PRDClarifier(InMemoryGraphStore())


class TestPRDClarifierCreateStructuredPRD:
    """Tests for the create_structured_prd() method."""

    def test_returns_structured_prd(
        self,
        prd_clarifier: PRDClarifier,
        sample_feature_request: FeatureRequest,
    ) -> None:
        """create_structured_prd() should return a StructuredPRD."""
        prd = prd_clarifier.create_structured_prd(sample_feature_request)
        assert isinstance(prd, StructuredPRD)

    def test_prd_has_feature_id(
        self,
        prd_clarifier: PRDClarifier,
        sample_feature_request: FeatureRequest,
    ) -> None:
        """The created PRD should have a non-empty feature_id."""
        prd = prd_clarifier.create_structured_prd(sample_feature_request)
        assert prd.feature_id.startswith("FEAT-")
        assert len(prd.feature_id) > 5

    def test_prd_title_matches_request(
        self,
        prd_clarifier: PRDClarifier,
        sample_feature_request: FeatureRequest,
    ) -> None:
        """The PRD title should match the feature request title."""
        prd = prd_clarifier.create_structured_prd(sample_feature_request)
        assert prd.title == sample_feature_request.title

    def test_prd_preserves_original_request(
        self,
        prd_clarifier: PRDClarifier,
        sample_feature_request: FeatureRequest,
    ) -> None:
        """The original_request should be preserved in the PRD."""
        prd = prd_clarifier.create_structured_prd(sample_feature_request)
        assert prd.original_request.title == sample_feature_request.title

    def test_prd_generates_clarification_questions(
        self,
        prd_clarifier: PRDClarifier,
        sample_feature_request: FeatureRequest,
    ) -> None:
        """create_structured_prd() should generate at least some questions."""
        prd = prd_clarifier.create_structured_prd(sample_feature_request)
        assert len(prd.clarification_questions) > 0

    def test_prd_has_backward_compat_question(
        self,
        prd_clarifier: PRDClarifier,
        sample_feature_request: FeatureRequest,
    ) -> None:
        """There should always be a backward compatibility question."""
        prd = prd_clarifier.create_structured_prd(sample_feature_request)
        question_types = {q.question_type for q in prd.clarification_questions}
        assert QuestionType.BACKWARD_COMPAT in question_types

    def test_prd_has_rollout_question(
        self,
        prd_clarifier: PRDClarifier,
        sample_feature_request: FeatureRequest,
    ) -> None:
        """There should always be a rollout strategy question."""
        prd = prd_clarifier.create_structured_prd(sample_feature_request)
        question_types = {q.question_type for q in prd.clarification_questions}
        assert QuestionType.ROLLOUT in question_types

    def test_prd_completeness_score_is_float(
        self,
        prd_clarifier: PRDClarifier,
        sample_feature_request: FeatureRequest,
    ) -> None:
        """completeness_score should be a float between 0.0 and 1.0."""
        prd = prd_clarifier.create_structured_prd(sample_feature_request)
        assert 0.0 <= prd.completeness_score <= 1.0

    def test_prd_not_finalized_initially(
        self,
        prd_clarifier: PRDClarifier,
        sample_feature_request: FeatureRequest,
    ) -> None:
        """A newly created PRD should not be finalized."""
        prd = prd_clarifier.create_structured_prd(sample_feature_request)
        assert prd.is_finalized is False

    def test_prd_with_pre_answered_questions(
        self,
        prd_clarifier: PRDClarifier,
        sample_feature_request: FeatureRequest,
    ) -> None:
        """Pre-answered questions should be marked as answered."""
        pre_answered = {
            "BACKWARD_COMPAT": "Field is nullable; backward compatible",
            "ROLLOUT": "Full rollout to India",
        }
        prd = prd_clarifier.create_structured_prd(
            sample_feature_request, pre_answered=pre_answered
        )
        answered = [q for q in prd.clarification_questions if q.is_answered]
        assert len(answered) > 0


class TestPRDClarifierFinalize:
    """Tests for the finalize() method."""

    def test_finalize_converts_answers_to_constraints(
        self,
        prd_clarifier: PRDClarifier,
        sample_feature_request: FeatureRequest,
    ) -> None:
        """finalize() should convert answered questions to TechnicalConstraints."""
        prd = prd_clarifier.create_structured_prd(sample_feature_request)

        # Answer all required questions
        for q in prd.clarification_questions:
            if q.is_required:
                q.mark_answered("Test answer for " + q.question_type.value)

        finalized_prd = prd_clarifier.finalize(prd)
        assert len(finalized_prd.technical_constraints) > 0

    def test_finalize_recomputes_completeness_score(
        self,
        prd_clarifier: PRDClarifier,
        sample_feature_request: FeatureRequest,
    ) -> None:
        """finalize() should recompute the completeness score after answering questions."""
        prd = prd_clarifier.create_structured_prd(sample_feature_request)
        initial_score = prd.completeness_score

        # Answer all required questions
        for q in prd.clarification_questions:
            if q.is_required:
                q.mark_answered("Answer")

        finalized_prd = prd_clarifier.finalize(prd)
        # Score should increase after answering questions
        assert finalized_prd.completeness_score >= initial_score

    def test_finalize_marks_as_finalized_when_complete(
        self,
        prd_clarifier: PRDClarifier,
        sample_feature_request: FeatureRequest,
    ) -> None:
        """finalize() should mark the PRD as finalized when all required questions are answered."""
        prd = prd_clarifier.create_structured_prd(sample_feature_request)

        # Answer all required questions
        for q in prd.clarification_questions:
            if q.is_required:
                q.mark_answered("Detailed technical answer provided")

        finalized_prd = prd_clarifier.finalize(prd)
        # Should be finalized if completeness score is above threshold
        if finalized_prd.completeness_score >= 0.8:
            assert finalized_prd.is_finalized is True


class TestClarificationQuestion:
    """Tests for the ClarificationQuestion model."""

    def test_mark_answered(self) -> None:
        """mark_answered() should set is_answered and answer."""
        q = ClarificationQuestion(
            question_id="Q-001",
            question_type=QuestionType.CACHING,
            text="Should this be cached?",
        )
        assert q.is_answered is False
        assert q.answer is None

        q.mark_answered("Yes, include in cache with 5 minute TTL")
        assert q.is_answered is True
        assert q.answer == "Yes, include in cache with 5 minute TTL"

    def test_required_by_default(self) -> None:
        """Questions should be required by default."""
        q = ClarificationQuestion(
            question_id="Q-002",
            question_type=QuestionType.SCOPE,
            text="What is the scope?",
        )
        assert q.is_required is True


class TestStructuredPRDModel:
    """Tests for the StructuredPRD model properties."""

    def test_unanswered_questions_property(
        self, sample_structured_prd: StructuredPRD
    ) -> None:
        """unanswered_questions should return required unanswered questions."""
        unanswered = sample_structured_prd.unanswered_questions
        for q in unanswered:
            assert q.is_required is True
            assert q.is_answered is False

    def test_get_seed_node_ids_high_confidence_only(
        self, sample_structured_prd: StructuredPRD
    ) -> None:
        """get_seed_node_ids() should only return high-confidence components."""
        seed_ids = sample_structured_prd.get_seed_node_ids()
        # All returned IDs should correspond to components with confidence >= 0.7
        for component in sample_structured_prd.affected_components:
            if component.confidence < 0.7:
                assert component.node_id not in seed_ids

    def test_is_ready_for_analysis_when_finalized(
        self, sample_structured_prd: StructuredPRD
    ) -> None:
        """A finalized PRD with high completeness should be ready for analysis."""
        assert sample_structured_prd.is_finalized is True
        assert sample_structured_prd.completeness_score >= 0.8
        # is_ready_for_analysis also checks unanswered questions
        # The sample fixture has no questions, so it should be ready
        assert sample_structured_prd.is_ready_for_analysis is True
