"""
PRD clarification engine for Professor v10.

Accepts a natural language feature description, uses the architecture graph
to identify potentially affected components, generates targeted clarification
questions, and iterates until the PRD is technically complete.

The clarifier operates in three modes:
1. Interactive (CLI): Presents questions to a human and collects answers
2. Batch: Processes a list of pre-answered questions from a config file
3. Inference: Automatically infers answers from graph context (where possible)

See docs/design/04-prd-clarification-engine.md for the full workflow design.
"""

from __future__ import annotations

import uuid

from src.graph.models import EntityType
from src.graph.query import GraphQueryEngine
from src.graph.store import GraphStore
from src.prd.models import (
    AffectedComponent,
    ClarificationQuestion,
    ComponentRole,
    ConstraintSource,
    FeatureRequest,
    QuestionType,
    StructuredPRD,
    TechnicalConstraint,
)


class PRDClarifier:
    """
    Transforms a raw feature request into a technically complete StructuredPRD.

    The clarifier uses the architecture graph to:
    1. Identify which services, DTOs, and components are potentially affected
    2. Generate context-aware clarification questions based on what the graph reveals
    3. Compute a completeness score to indicate when the PRD is ready for analysis

    Usage:
        clarifier = PRDClarifier(graph_store)
        prd = clarifier.create_structured_prd(feature_request)
        questions = prd.unanswered_questions
        # Present questions to stakeholder, collect answers...
        for q, answer in zip(questions, answers):
            q.mark_answered(answer)
        prd = clarifier.finalize(prd)
    """

    def __init__(self, store: GraphStore) -> None:
        """
        Initialize the clarifier with a populated graph store.

        The graph store must be fully constructed before clarification begins,
        as the clarifier queries it to identify affected components and generate
        context-aware questions.

        Args:
            store: The architecture graph store to query.
        """
        self._store = store
        self._query_engine = GraphQueryEngine(store)

    def create_structured_prd(
        self,
        feature_request: FeatureRequest,
        pre_answered: dict[str, str] | None = None,
    ) -> StructuredPRD:
        """
        Create an initial StructuredPRD from a raw feature request.

        This method:
        1. Extracts domain entities from the feature description
        2. Identifies affected components in the architecture graph
        3. Generates clarification questions based on what the graph reveals
        4. Computes initial completeness score

        Args:
            feature_request: The raw feature request to process.
            pre_answered: Optional dict of {question_type: answer} for
                questions that are already known (e.g., from a config file).

        Returns:
            StructuredPRD with initial affected components and questions.
            Will have completeness_score < 1.0 until all questions are answered.
        """
        feature_id = str(uuid.uuid4())[:8].upper()

        # Step 1: Identify affected components from the graph
        affected_components = self._identify_affected_components(feature_request)

        # Step 2: Generate clarification questions based on feature + graph context
        questions = self._generate_clarification_questions(
            feature_request, affected_components
        )

        # Step 3: Auto-answer questions where the graph provides the answer
        questions = self._infer_answers_from_graph(questions, affected_components)

        # Step 4: Apply pre-answered responses if provided
        if pre_answered:
            for question in questions:
                if question.question_type.value in pre_answered:
                    question.mark_answered(pre_answered[question.question_type.value])

        # Step 5: Build initial PRD
        prd = StructuredPRD(
            feature_id=f"FEAT-{feature_id}",
            title=feature_request.title,
            original_request=feature_request,
            affected_components=affected_components,
            clarification_questions=questions,
        )

        # Step 6: Compute completeness score
        prd.completeness_score = self._compute_completeness_score(prd)

        return prd

    def finalize(self, prd: StructuredPRD) -> StructuredPRD:
        """
        Finalize a StructuredPRD after all clarification questions have been answered.

        This method:
        1. Converts answered questions into TechnicalConstraints
        2. Recomputes the completeness score
        3. Identifies any remaining missing constraints
        4. Marks the PRD as finalized if complete

        Args:
            prd: The StructuredPRD with answered questions.

        Returns:
            Updated StructuredPRD with technical constraints and final score.
        """
        # Convert answered questions to technical constraints
        constraints = self._extract_constraints_from_answers(prd)
        prd.technical_constraints = constraints

        # Recompute completeness
        prd.completeness_score = self._compute_completeness_score(prd)
        prd.missing_constraints = self._identify_missing_constraints(prd)

        # Mark as finalized if ready
        if prd.is_ready_for_analysis:
            prd.is_finalized = True

        return prd

    # -------------------------------------------------------------------------
    # Component identification
    # -------------------------------------------------------------------------

    def _identify_affected_components(
        self, feature_request: FeatureRequest
    ) -> list[AffectedComponent]:
        """
        Search the architecture graph for components related to the feature request.

        Uses keyword extraction from the feature description to identify candidate
        components, then queries the graph for matches.

        Args:
            feature_request: The raw feature request.

        Returns:
            List of AffectedComponent objects identified from the graph.
        """
        # TODO: Implement full affected component identification
        # Algorithm:
        # 1. Extract domain keywords from feature_request.description:
        #    - PascalCase words → class names (DTOs, services)
        #    - Domain nouns → service names ("coupon" → coupon-engine)
        #    - Field names (camelCase) → DTO field names
        # 2. For each keyword, query the graph:
        #    - Exact name match on nodes
        #    - Partial name match (fuzzy) on nodes
        #    - Domain-based match (repo name contains keyword)
        # 3. Expand the initial match set via graph traversal:
        #    - If a DTO is matched, also add the service that owns it
        #    - If a service is matched, also add its endpoints and caches
        # 4. Assign ComponentRole to each identified component:
        #    - Service with CONTROLLER type → EXPOSES_API
        #    - DTO in response → OWNS_CONTRACT
        #    - Dart ModelNode → MAPS_FRONTEND
        #    - CacheNode → USES_CACHE
        # 5. Assign confidence scores:
        #    - Exact name match: 0.90
        #    - Domain match only: 0.65
        #    - Indirect graph neighbor: 0.50
        #
        # For Phase 1: basic keyword search against graph node names

        components: list[AffectedComponent] = []

        # Extract candidate names from the feature description
        candidate_names = self._extract_entity_names(feature_request.description)

        for candidate in candidate_names:
            # Search graph for nodes with matching names
            matches = [
                entity
                for entity in self._store.all_nodes()
                if candidate.lower() in entity.name.lower()
            ]
            for entity in matches:
                role = self._infer_component_role(entity)
                components.append(
                    AffectedComponent(
                        node_id=entity.id,
                        name=entity.name,
                        component_type=entity.entity_type.value,
                        repo=entity.repo,
                        language=entity.language.value,
                        role=role,
                        reason=f"Name contains keyword '{candidate}' from feature description",
                        confidence=0.75,
                    )
                )

        return components

    def _extract_entity_names(self, text: str) -> list[str]:
        """
        Extract potential entity names (PascalCase and key domain nouns) from text.

        Args:
            text: Natural language text to extract names from.

        Returns:
            List of candidate entity name strings.
        """
        import re  # noqa: PLC0415

        # TODO: Implement richer entity extraction
        # Phase 1: extract PascalCase words as potential class names
        pascal_case = re.findall(r"\b[A-Z][a-zA-Z0-9]+\b", text)

        # Also extract significant domain nouns (multi-word → single key terms)
        # For now: extract words longer than 4 characters that aren't common words
        stop_words = {"that", "this", "with", "from", "into", "about", "should", "would"}
        long_words = [w.lower() for w in re.findall(r"\b[a-zA-Z]{5,}\b", text)
                      if w.lower() not in stop_words]

        return list(set(pascal_case + long_words))

    def _infer_component_role(self, entity) -> ComponentRole:
        """
        Infer the ComponentRole for a given entity based on its type and language.

        Args:
            entity: A CodeEntity from the graph.

        Returns:
            The most likely ComponentRole for this entity.
        """
        if entity.entity_type in (EntityType.MODEL, EntityType.DTO):
            if entity.language.value == "java":
                return ComponentRole.OWNS_CONTRACT
            else:
                return ComponentRole.MAPS_FRONTEND
        elif entity.entity_type == EntityType.CONTROLLER:
            return ComponentRole.EXPOSES_API
        elif entity.entity_type == EntityType.SERVICE:
            return ComponentRole.PRODUCES_DATA
        elif entity.entity_type == EntityType.CACHE:
            return ComponentRole.USES_CACHE
        elif entity.entity_type == EntityType.DATABASE:
            return ComponentRole.READS_DB
        else:
            return ComponentRole.CONSUMES_API

    # -------------------------------------------------------------------------
    # Question generation
    # -------------------------------------------------------------------------

    def _generate_clarification_questions(
        self,
        feature_request: FeatureRequest,
        affected_components: list[AffectedComponent],
    ) -> list[ClarificationQuestion]:
        """
        Generate targeted clarification questions based on the feature and graph context.

        Questions are generated from two sources:
        1. Standard questions always asked for any feature (backward compat, rollout, etc.)
        2. Graph-informed questions triggered by specific component types found in the graph
           (e.g., if a cache is affected → ask about cache invalidation strategy)

        Args:
            feature_request: The original feature request.
            affected_components: Components identified from the graph.

        Returns:
            List of ClarificationQuestion objects.
        """
        questions: list[ClarificationQuestion] = []

        # Standard questions (always asked)
        questions.extend(self._standard_questions(feature_request))

        # Graph-informed questions (triggered by component types)
        has_cache = any(c.role == ComponentRole.USES_CACHE for c in affected_components)
        has_frontend = any(c.role == ComponentRole.MAPS_FRONTEND for c in affected_components)
        has_db = any(c.role in (ComponentRole.READS_DB, ComponentRole.WRITES_DB)
                     for c in affected_components)

        if has_cache:
            questions.append(self._cache_question(affected_components))

        if has_frontend:
            questions.append(self._frontend_compat_question(affected_components))

        if has_db:
            questions.append(self._database_question(affected_components))

        return questions

    def _standard_questions(
        self, feature_request: FeatureRequest
    ) -> list[ClarificationQuestion]:
        """
        Generate the standard set of questions asked for every feature.

        These cover the most common sources of PRD ambiguity regardless
        of the specific feature content.
        """
        return [
            ClarificationQuestion(
                question_id=f"Q-{uuid.uuid4().hex[:6]}",
                question_type=QuestionType.BACKWARD_COMPAT,
                text=(
                    "Is this change backward compatible with existing API consumers "
                    "and mobile app versions currently in production? "
                    "If adding a new field, should it be nullable to support older clients?"
                ),
                is_required=True,
                context="Backward compatibility is required for zero-downtime deployments.",
            ),
            ClarificationQuestion(
                question_id=f"Q-{uuid.uuid4().hex[:6]}",
                question_type=QuestionType.ROLLOUT,
                text=(
                    "What is the rollout strategy? "
                    "Options: (a) Full rollout to all users, "
                    "(b) Phased rollout by country/segment, "
                    "(c) A/B test, "
                    "(d) Feature flag guarded."
                ),
                is_required=True,
                context="Rollout strategy determines deployment risk and testing approach.",
            ),
            ClarificationQuestion(
                question_id=f"Q-{uuid.uuid4().hex[:6]}",
                question_type=QuestionType.SCOPE,
                text=(
                    "What is the scope of this feature? "
                    "Should it apply to all users globally, or a specific "
                    "country, user segment, or account tier?"
                ),
                is_required=True,
                context="Scope determines which configuration flags and data segmentation is needed.",
            ),
            ClarificationQuestion(
                question_id=f"Q-{uuid.uuid4().hex[:6]}",
                question_type=QuestionType.FEATURE_FLAG,
                text=(
                    "Should this feature be behind a feature flag for controlled rollout? "
                    "If yes, what should the flag be named and what is the default value?"
                ),
                is_required=False,
                context="Feature flags enable safe rollout and instant rollback.",
            ),
        ]

    def _cache_question(
        self, affected_components: list[AffectedComponent]
    ) -> ClarificationQuestion:
        """Generate a cache-specific clarification question."""
        cache_names = [c.name for c in affected_components if c.role == ComponentRole.USES_CACHE]
        cache_context = f"Affected caches: {', '.join(cache_names)}" if cache_names else ""

        return ClarificationQuestion(
            question_id=f"Q-{uuid.uuid4().hex[:6]}",
            question_type=QuestionType.CACHING,
            text=(
                "The architecture graph shows that affected services use caching. "
                "Should the new data be included in the cached response, or served fresh? "
                "If cached, does the cache key need to be updated to include the new data dimensions? "
                "What is the acceptable staleness window (cache TTL)?"
            ),
            is_required=True,
            context=cache_context,
            graph_evidence=[c.node_id for c in affected_components if c.role == ComponentRole.USES_CACHE],
        )

    def _frontend_compat_question(
        self, affected_components: list[AffectedComponent]
    ) -> ClarificationQuestion:
        """Generate a frontend model compatibility question."""
        frontend_names = [c.name for c in affected_components if c.role == ComponentRole.MAPS_FRONTEND]

        return ClarificationQuestion(
            question_id=f"Q-{uuid.uuid4().hex[:6]}",
            question_type=QuestionType.CONSUMERS,
            text=(
                f"The following frontend models will need to be updated: "
                f"{', '.join(frontend_names) if frontend_names else 'Dart/TypeScript models'}. "
                "Are there any mobile app version constraints? "
                "What is the minimum supported app version that should receive this new data?"
            ),
            is_required=True,
            context="Frontend models must be updated to reflect backend DTO changes.",
            graph_evidence=[c.node_id for c in affected_components if c.role == ComponentRole.MAPS_FRONTEND],
        )

    def _database_question(
        self, affected_components: list[AffectedComponent]
    ) -> ClarificationQuestion:
        """Generate a database schema change question."""
        return ClarificationQuestion(
            question_id=f"Q-{uuid.uuid4().hex[:6]}",
            question_type=QuestionType.SCHEMA,
            text=(
                "The architecture graph shows database interaction in the affected services. "
                "Does this feature require any database schema changes (new columns, tables, indexes)? "
                "If yes, is a backward-compatible migration plan in place?"
            ),
            is_required=True,
            context="Database schema changes require careful migration planning to avoid downtime.",
        )

    # -------------------------------------------------------------------------
    # Answer inference and constraint extraction
    # -------------------------------------------------------------------------

    def _infer_answers_from_graph(
        self,
        questions: list[ClarificationQuestion],
        affected_components: list[AffectedComponent],
    ) -> list[ClarificationQuestion]:
        """
        Auto-answer questions where the architecture graph provides sufficient context.

        Some questions can be answered by the graph itself — for example,
        if the graph shows no cache nodes, the caching question can be marked
        as "not applicable". This reduces the clarification burden on stakeholders.

        Args:
            questions: The generated clarification questions.
            affected_components: Identified affected components.

        Returns:
            Questions with graph-inferred answers where applicable.
        """
        # TODO: Implement graph-based answer inference
        # Examples of inferrable answers:
        # - No cache nodes in affected components → CACHING question: "Not applicable"
        # - No Dart/TS nodes in graph at all → frontend question: "No frontend applicable"
        # - Single repo affected → SCOPE inference: "Scoped to {repo_name} service"
        # - Feature flags in code → FEATURE_FLAG: "Existing flag mechanism available"
        return questions

    def _extract_constraints_from_answers(
        self, prd: StructuredPRD
    ) -> list[TechnicalConstraint]:
        """
        Convert answered clarification questions into TechnicalConstraint objects.

        Each answered question contributes one or more TechnicalConstraints
        to the structured PRD.

        Args:
            prd: The StructuredPRD with answered questions.

        Returns:
            List of TechnicalConstraint objects derived from the answers.
        """
        constraints = []

        for question in prd.clarification_questions:
            if question.is_answered and question.answer:
                constraints.append(
                    TechnicalConstraint(
                        constraint_type=question.question_type,
                        description=f"{question.question_type.value}: {question.answer}",
                        source=ConstraintSource.CLARIFICATION_ANSWER,
                        raw_answer=question.answer,
                    )
                )

        return constraints

    # -------------------------------------------------------------------------
    # Completeness scoring
    # -------------------------------------------------------------------------

    def _compute_completeness_score(self, prd: StructuredPRD) -> float:
        """
        Compute a completeness score (0.0–1.0) for the current state of the PRD.

        Scoring factors:
        - Required questions answered: 60% weight
        - Affected components identified with high confidence: 20% weight
        - Optional questions answered: 10% weight
        - Constraints resolved: 10% weight

        Args:
            prd: The StructuredPRD to score.

        Returns:
            Float between 0.0 and 1.0 representing PRD completeness.
        """
        required_questions = [q for q in prd.clarification_questions if q.is_required]
        optional_questions = [q for q in prd.clarification_questions if not q.is_required]

        # Factor 1: Required questions answered (60% weight)
        if required_questions:
            required_score = sum(1 for q in required_questions if q.is_answered) / len(required_questions)
        else:
            required_score = 1.0

        # Factor 2: High-confidence affected components (20% weight)
        if prd.affected_components:
            high_conf = sum(1 for c in prd.affected_components if c.confidence >= 0.7)
            component_score = min(1.0, high_conf / max(1, len(prd.affected_components)))
        else:
            component_score = 0.5  # Partial credit if no components found yet

        # Factor 3: Optional questions answered (10% weight)
        if optional_questions:
            optional_score = sum(1 for q in optional_questions if q.is_answered) / len(optional_questions)
        else:
            optional_score = 1.0

        # Factor 4: Constraints resolved (10% weight)
        constraint_score = min(1.0, len(prd.technical_constraints) / max(1, len(required_questions)))

        return round(
            0.60 * required_score
            + 0.20 * component_score
            + 0.10 * optional_score
            + 0.10 * constraint_score,
            2,
        )

    def _identify_missing_constraints(self, prd: StructuredPRD) -> list[str]:
        """
        Identify which technical constraint categories are still missing.

        Args:
            prd: The StructuredPRD to check.

        Returns:
            List of human-readable descriptions of missing constraints.
        """
        missing = []

        answered_types = {c.constraint_type for c in prd.technical_constraints}
        required_types = {
            q.question_type for q in prd.clarification_questions if q.is_required
        }

        for qt in required_types:
            if qt not in answered_types:
                missing.append(f"Missing constraint for: {qt.value}")

        return missing
