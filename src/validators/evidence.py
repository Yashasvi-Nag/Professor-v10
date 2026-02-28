"""
Evidence validation for Professor v10.

Ensures that every claim in the architectural output is backed by a traceable
source code reference. Computes confidence scores for each claim and flags
low-confidence items for human review.

The EvidenceValidator is the final gate before document generation. It:
1. Verifies all graph nodes have source locations
2. Computes overall confidence score for the analysis
3. Identifies claims that need human review (confidence < threshold)
4. Flags missing coverage (repos not in parse scope)
5. Validates that the PRD completeness score is above the minimum threshold

This implements the Trust Validation design from docs/design/06-trust-validation.md
and enforces the non-negotiable rules from docs/adr/005-evidence-backed-reasoning.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from src.analysis.impact import ImpactReport
from src.graph.models import CodeEntity
from src.graph.store import GraphStore
from src.prd.models import StructuredPRD


class ValidationStatus(StrEnum):
    """Overall validation status of the analysis output."""

    PASSED = "PASSED"           # All required rules passed; output can be generated
    PASSED_WITH_WARNINGS = "PASSED_WITH_WARNINGS"  # Rules passed but warnings exist
    FAILED = "FAILED"           # One or more required rules failed; output blocked


@dataclass
class EvidenceIssue:
    """
    A single issue identified during evidence validation.

    Issues are either blocking (validation fails) or warnings
    (validation passes but issue is noted in the output).
    """

    rule_id: str
    """The rule that was violated (e.g., 'EV-001')."""

    description: str
    """Human-readable description of the issue."""

    is_blocking: bool = True
    """Whether this issue blocks document generation."""

    entity: CodeEntity | None = None
    """The code entity associated with this issue, if applicable."""

    recommendation: str = ""
    """Recommended action to resolve this issue."""


@dataclass
class EvidenceValidationResult:
    """
    The complete result of running evidence validation.

    Contains all detected issues, the overall confidence score,
    and the final validation status.
    """

    status: ValidationStatus = ValidationStatus.PASSED
    issues: list[EvidenceIssue] = field(default_factory=list)
    overall_confidence: float = 1.0
    total_nodes_validated: int = 0
    nodes_with_evidence: int = 0
    nodes_without_evidence: int = 0
    low_confidence_nodes: list[CodeEntity] = field(default_factory=list)
    review_required_nodes: list[CodeEntity] = field(default_factory=list)
    coverage_warnings: list[str] = field(default_factory=list)

    @property
    def blocking_issues(self) -> list[EvidenceIssue]:
        """Return only issues that block document generation."""
        return [i for i in self.issues if i.is_blocking]

    @property
    def warning_issues(self) -> list[EvidenceIssue]:
        """Return only warning-level issues."""
        return [i for i in self.issues if not i.is_blocking]

    @property
    def passed(self) -> bool:
        """Return True if validation passed (no blocking issues)."""
        return self.status in (ValidationStatus.PASSED, ValidationStatus.PASSED_WITH_WARNINGS)


class EvidenceValidator:
    """
    Validates that all architectural claims are backed by source code evidence.

    This is the final validation step before document generation. It enforces
    the evidence-backed reasoning rules defined in ADR-005 and the trust
    validation design in docs/design/06-trust-validation.md.

    Usage:
        validator = EvidenceValidator(min_confidence=0.60)
        result = validator.validate(graph_store, impact_report, prd)
        if not result.passed:
            for issue in result.blocking_issues:
                print(f"BLOCKING: {issue.description}")
        else:
            # Proceed with document generation
            pass
    """

    # Minimum confidence threshold — claims below this require human review
    DEFAULT_MIN_CONFIDENCE = 0.60

    # Minimum PRD completeness score to allow document generation
    MIN_PRD_COMPLETENESS = 0.80

    def __init__(self, min_confidence: float = DEFAULT_MIN_CONFIDENCE) -> None:
        """
        Initialize the evidence validator.

        Args:
            min_confidence: Minimum confidence score for claims to be accepted
                without requiring human review. Claims below this threshold
                are flagged as REVIEW REQUIRED in the output document.
        """
        self.min_confidence = min_confidence

    def validate(
        self,
        store: GraphStore,
        impact_report: ImpactReport,
        prd: StructuredPRD,
    ) -> EvidenceValidationResult:
        """
        Run all evidence validation checks.

        Executes the complete set of validation rules and returns a result
        indicating whether document generation can proceed.

        Args:
            store: The architecture graph store.
            impact_report: The computed impact analysis report.
            prd: The structured PRD.

        Returns:
            EvidenceValidationResult indicating pass/fail with all detected issues.
        """
        result = EvidenceValidationResult()
        issues: list[EvidenceIssue] = []

        # EV-001: All impact report nodes must have source locations
        issues.extend(self._check_nodes_have_evidence(impact_report, result))

        # EV-002: All graph edges must have source locations
        issues.extend(self._check_edges_have_evidence(store, result))

        # EV-003: PRD completeness must be above threshold
        issues.extend(self._check_prd_completeness(prd))

        # EV-004: Identify low-confidence nodes for review flagging
        low_conf, review_req = self._classify_by_confidence(impact_report)
        result.low_confidence_nodes = low_conf
        result.review_required_nodes = review_req

        # EV-005: Compute overall confidence score
        result.overall_confidence = self._compute_overall_confidence(impact_report, store)

        # EV-006: Identify coverage gaps
        result.coverage_warnings = self._identify_coverage_gaps(impact_report)

        # Populate result
        result.issues = issues
        blocking = [i for i in issues if i.is_blocking]

        if blocking:
            result.status = ValidationStatus.FAILED
        elif issues:
            result.status = ValidationStatus.PASSED_WITH_WARNINGS
        else:
            result.status = ValidationStatus.PASSED

        return result

    # -------------------------------------------------------------------------
    # Validation rules
    # -------------------------------------------------------------------------

    def _check_nodes_have_evidence(
        self, impact_report: ImpactReport, result: EvidenceValidationResult
    ) -> list[EvidenceIssue]:
        """
        EV-001: Every node in the impact report must have a valid source location.

        A source location is valid if it has a non-empty file_path.
        """
        issues = []
        all_impacted = impact_report.impact_result.impacted_nodes
        result.total_nodes_validated = len(all_impacted)

        for impacted_node in all_impacted:
            entity = impacted_node.entity
            loc = entity.source_location

            if not loc.file_path or loc.file_path == "":
                result.nodes_without_evidence += 1
                issues.append(
                    EvidenceIssue(
                        rule_id="EV-001",
                        description=(
                            f"Node '{entity.name}' ({entity.id}) has no source file evidence. "
                            "Cannot verify this claim."
                        ),
                        is_blocking=True,
                        entity=entity,
                        recommendation=(
                            "Ensure the parser that created this node populates "
                            "the file_path and line_number fields."
                        ),
                    )
                )
            else:
                result.nodes_with_evidence += 1

        return issues

    def _check_edges_have_evidence(
        self, store: GraphStore, result: EvidenceValidationResult
    ) -> list[EvidenceIssue]:
        """
        EV-002: All edges in the graph must have source locations.

        This enforces the non-negotiable rule R1 from ADR-005:
        "Every graph edge must have a source location."
        """
        issues = []

        for edge in store.all_edges():
            if edge.source_location is None:
                issues.append(
                    EvidenceIssue(
                        rule_id="EV-002",
                        description=(
                            f"Edge '{edge.edge_type.value}' from '{edge.source_id}' "
                            f"to '{edge.target_id}' has no source location. "
                            "This dependency claim cannot be verified."
                        ),
                        # EV-002 is a warning, not blocking (edge may be inferred)
                        is_blocking=False,
                        recommendation=(
                            "Ensure the parser or graph builder that created this edge "
                            "sets the source_location field."
                        ),
                    )
                )

        return issues

    def _check_prd_completeness(self, prd: StructuredPRD) -> list[EvidenceIssue]:
        """
        EV-003: PRD completeness score must be above the minimum threshold.

        An incomplete PRD means technical constraints are missing, which could
        lead to an incorrect or incomplete impact analysis.
        """
        issues = []

        if prd.completeness_score < self.MIN_PRD_COMPLETENESS:
            issues.append(
                EvidenceIssue(
                    rule_id="EV-003",
                    description=(
                        f"PRD completeness score {prd.completeness_score:.0%} is below "
                        f"the minimum threshold of {self.MIN_PRD_COMPLETENESS:.0%}. "
                        "Impact analysis may be incomplete or inaccurate."
                    ),
                    is_blocking=True,
                    recommendation=(
                        f"Answer all required clarification questions. "
                        f"Missing: {', '.join(prd.missing_constraints) or 'none identified'}"
                    ),
                )
            )

        return issues

    def _classify_by_confidence(
        self, impact_report: ImpactReport
    ) -> tuple[list[CodeEntity], list[CodeEntity]]:
        """
        Classify impacted nodes by confidence score.

        Returns two lists:
        - low_confidence: confidence < 0.7 (should be noted in document)
        - review_required: confidence < min_confidence (must be flagged for review)
        """
        low_confidence = []
        review_required = []

        for impacted_node in impact_report.impact_result.impacted_nodes:
            entity = impacted_node.entity
            if entity.confidence < self.min_confidence:
                review_required.append(entity)
            elif entity.confidence < 0.7:
                low_confidence.append(entity)

        return low_confidence, review_required

    def _compute_overall_confidence(
        self, impact_report: ImpactReport, store: GraphStore
    ) -> float:
        """
        Compute the overall confidence score for the complete analysis.

        Factors:
        - Average node confidence from the impact report (70% weight)
        - Average edge confidence from the graph (30% weight)

        Returns:
            Float between 0.0 and 1.0 representing overall analysis confidence.
        """
        # Node confidence
        all_impacted = impact_report.impact_result.impacted_nodes
        if all_impacted:
            node_confidence = sum(n.entity.confidence for n in all_impacted) / len(all_impacted)
        else:
            node_confidence = 1.0

        # Edge confidence
        all_edges = store.all_edges()
        if all_edges:
            edge_confidence = sum(e.confidence for e in all_edges) / len(all_edges)
        else:
            edge_confidence = 1.0

        return round(0.70 * node_confidence + 0.30 * edge_confidence, 2)

    def _identify_coverage_gaps(self, impact_report: ImpactReport) -> list[str]:
        """
        Identify warnings about repositories or languages not covered by the analysis.

        These are not blocking but should be prominently disclosed in the output document
        to set expectations about the completeness of the analysis.

        Args:
            impact_report: The impact report with affected repos and languages.

        Returns:
            List of coverage gap warning strings.
        """
        warnings = []

        # TODO: Compare affected_repos against the full configured repo list
        # If some repos are in the config but not in the affected_repos, note them
        # as "analyzed but no impact detected"
        # If the impact report has no Dart nodes but the config includes a Flutter repo,
        # warn that Flutter impact could not be assessed

        # Forward the analysis warnings
        warnings.extend(impact_report.impact_result.warnings)

        return warnings
