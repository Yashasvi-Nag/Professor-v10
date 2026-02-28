"""
Java / Spring Boot parser for Professor v10.

Extracts architectural entities from Java source files, focusing on:
- Spring Boot REST controllers and their endpoints
- Data Transfer Objects (DTOs, request/response classes)
- Service classes and their dependencies
- Feign client declarations (inter-service HTTP calls)
- Kafka producer and consumer declarations
- Redis/cache annotation usage
- JPA entities and repositories
- Feature flags and configuration properties

Detection strategy (Phase 1):
- Regex-based annotation and class signature detection
- Line-by-line scanning with context accumulation
- No full AST parsing in Phase 1 (tree-sitter integration planned for Phase 2)

See docs/design/01-code-graph-extraction.md for full design rationale.
"""

import re
from pathlib import Path

from src.graph.models import (
    CacheNode,
    CodeEntity,
    DependencyEdge,
    EndpointNode,
    EntityType,
    Language,
    MessageTopicNode,
    ModelNode,
    ServiceNode,
    SourceLocation,
)
from src.parsers.base import BaseParser


class JavaParser(BaseParser):
    """
    Parser for Java/Spring Boot repositories.

    Scans .java files and extracts Spring Boot architectural entities
    using annotation-based detection heuristics.
    """

    @property
    def language(self) -> str:
        return "java"

    def parse(self, repo_path: str) -> list[CodeEntity]:
        """
        Parse a Java/Spring Boot repository and extract all architectural entities.

        Scans all .java files in the repository, identifies Spring Boot components
        via annotation detection, and builds CodeEntity objects.

        Args:
            repo_path: Absolute path to the Java repository root.

        Returns:
            Flat list of all CodeEntity objects found in the repository.
        """
        self._repo_path = repo_path
        self._parsed_entities = []

        java_files = self._scan_files(repo_path, [".java"])

        for file_path in java_files:
            # Skip test files by default (configurable via ParserSettings)
            if self._is_test_file(file_path):
                continue

            content = self._read_file(file_path)
            if content is None:
                continue

            entities = self._parse_file(file_path, content)
            self._parsed_entities.extend(entities)

        return self._parsed_entities

    def extract_endpoints(self) -> list[EndpointNode]:
        """
        Extract REST API endpoint definitions from parsed Java files.

        Returns EndpointNode for each HTTP mapping annotation found
        (@GetMapping, @PostMapping, @PutMapping, @DeleteMapping, @PatchMapping,
        @RequestMapping on controller methods).

        Returns:
            List of EndpointNode objects, one per HTTP endpoint.
        """
        return [e for e in self._parsed_entities if isinstance(e, EndpointNode)]

    def extract_models(self) -> list[ModelNode]:
        """
        Extract DTO and JPA entity definitions from parsed Java files.

        Returns ModelNode for classes that appear to be data transfer objects
        or JPA entities (naming conventions + annotation detection).

        Returns:
            List of ModelNode objects representing Java DTOs and entities.
        """
        return [e for e in self._parsed_entities if isinstance(e, ModelNode)]

    def extract_dependencies(self) -> list[DependencyEdge]:
        """
        Extract inter-service dependency declarations (Feign clients, etc.).

        Returns DependencyEdge objects for each @FeignClient declaration found,
        representing synchronous service-to-service call relationships.

        Returns:
            List of DependencyEdge objects representing declared dependencies.
        """
        # TODO: Return DependencyEdge objects extracted during parse()
        # These are accumulated in a separate list during _parse_file()
        return []

    def extract_cache_usage(self) -> list[CacheNode]:
        """
        Extract cache usage annotations from parsed Java files.

        Detects: @Cacheable, @CacheEvict, @CachePut, RedisTemplate usage.

        Returns:
            List of CacheNode objects representing cache interaction points.
        """
        return [e for e in self._parsed_entities if isinstance(e, CacheNode)]

    def extract_messaging(self) -> list[MessageTopicNode]:
        """
        Extract Kafka producer and consumer declarations.

        Detects: @KafkaListener(topics=...), KafkaTemplate.send(topic, ...).

        Returns:
            List of MessageTopicNode objects representing Kafka topic interactions.
        """
        return [e for e in self._parsed_entities if isinstance(e, MessageTopicNode)]

    # -------------------------------------------------------------------------
    # Private parsing methods
    # -------------------------------------------------------------------------

    def _parse_file(self, file_path: Path, content: str) -> list[CodeEntity]:
        """
        Parse a single Java file and extract all entities found within it.

        Args:
            file_path: Path to the .java file.
            content: File contents as a string.

        Returns:
            List of CodeEntity objects extracted from this file.
        """
        entities: list[CodeEntity] = []
        lines = content.splitlines()
        repo_name = self._infer_repo_name()

        # TODO: Implement full Java file parsing
        # The implementation should perform the following steps:
        #
        # 1. Detect package declaration (line starting with "package ")
        # 2. Detect class declaration and annotations above it:
        #    - @RestController or @Controller → ServiceNode (controller)
        #    - @Service → ServiceNode (service)
        #    - @FeignClient(name="...") → extract target service name
        #    - @Entity → ModelNode (JPA entity)
        #    - @Repository → ServiceNode (repository)
        #    - @KafkaListener → MessageTopicNode
        #    - DTO naming: *Dto, *Request, *Response, *VO → ModelNode
        # 3. Detect method-level annotations:
        #    - @GetMapping, @PostMapping, @PutMapping, @DeleteMapping, @PatchMapping
        #      → EndpointNode with HTTP method and path extracted from annotation value
        #    - @Cacheable, @CacheEvict, @CachePut → CacheNode with key extracted
        #    - @KafkaListener(topics="{topic}") → MessageTopicNode (consumer)
        # 4. Detect field-level patterns:
        #    - KafkaTemplate.send("topic", ...) → MessageTopicNode (producer)
        #    - RedisTemplate usage → CacheNode
        #    - @Autowired or constructor injection of @FeignClient → DependencyEdge
        # 5. For each detected entity, create a CodeEntity with:
        #    - source_location pointing to the exact line in this file
        #    - repo set to repo_name
        #    - language set to Language.JAVA
        #
        # See: docs/design/01-code-graph-extraction.md for entity types and
        # detection strategies.

        # Placeholder: detect @RestController as a minimal example
        for line_num, line in enumerate(lines, start=1):
            if "@RestController" in line or "@Controller" in line:
                class_name = self._extract_class_name(lines, line_num)
                if class_name:
                    entities.append(
                        ServiceNode(
                            id=f"{repo_name}/java/controller/{class_name}",
                            name=class_name,
                            entity_type=EntityType.CONTROLLER,
                            language=Language.JAVA,
                            file_path=str(file_path),
                            line_number=line_num,
                            repo=repo_name,
                            metadata={"annotation": "@RestController"},
                        )
                    )

        return entities

    def _extract_class_name(self, lines: list[str], annotation_line: int) -> str | None:
        """
        Find the class name declared after an annotation line.

        Scans forward from the annotation to find the class declaration,
        handling cases where annotations and class declaration are separated
        by other annotations or blank lines.

        Args:
            lines: All lines in the file.
            annotation_line: 1-based line number of the annotation.

        Returns:
            Class name string, or None if not found within 5 lines.
        """
        # TODO: Implement robust class name extraction
        # Should handle:
        # - Multi-line annotations (@RequestMapping(\n    value = "..."\n))
        # - Multiple stacked annotations
        # - Access modifiers and generics: "public class UserController<T>"
        # - Abstract/final modifiers
        class_pattern = re.compile(r"\bclass\s+(\w+)")
        for i in range(annotation_line, min(annotation_line + 5, len(lines))):
            match = class_pattern.search(lines[i])
            if match:
                return match.group(1)
        return None

    def _extract_annotation_value(self, line: str, annotation: str) -> str | None:
        """
        Extract the value from an annotation like @GetMapping("/path").

        Handles both simple string values and named parameters like
        @RequestMapping(value = "/path", method = RequestMethod.GET).

        Args:
            line: Source line containing the annotation.
            annotation: Annotation name without @ (e.g., "GetMapping").

        Returns:
            The extracted string value, or None if not found.
        """
        # TODO: Implement annotation value extraction
        # Should handle:
        # @GetMapping("/path") → "/path"
        # @GetMapping(value = "/path") → "/path"
        # @FeignClient(name = "coupon-engine") → "coupon-engine"
        # @KafkaListener(topics = "${kafka.topic.orders}") → "${kafka.topic.orders}"
        pattern = re.compile(rf'@{annotation}\s*\(\s*["\']([^"\']+)["\']')
        match = pattern.search(line)
        if match:
            return match.group(1)
        return None

    def _is_test_file(self, file_path: Path) -> bool:
        """
        Determine if a file is a test file that should be excluded from analysis.

        Checks for:
        - Files in src/test/ directory
        - Files ending in Test.java, Tests.java, IT.java (integration tests)
        - Files in packages containing "test"

        Args:
            file_path: Path to the file being checked.

        Returns:
            True if the file appears to be a test file.
        """
        path_str = str(file_path).lower()
        return (
            "/src/test/" in path_str
            or "/test/" in path_str
            or file_path.stem.endswith("Test")
            or file_path.stem.endswith("Tests")
            or file_path.stem.endswith("IT")
        )

    def _infer_repo_name(self) -> str:
        """
        Infer the repository name from the repo path.

        Returns:
            Repository name string (last component of the repo path).
        """
        if self._repo_path:
            return Path(self._repo_path).name
        return "unknown-repo"

    def _build_source_location(self, file_path: Path, line_number: int) -> SourceLocation:
        """
        Build a SourceLocation for evidence linking.

        Args:
            file_path: Path to the source file.
            line_number: 1-based line number.

        Returns:
            SourceLocation with repo, file path, and line number populated.
        """
        return SourceLocation(
            repo=self._infer_repo_name(),
            file_path=str(file_path),
            line_number=line_number,
        )
