"""
Abstract base parser defining the interface all language parsers must implement.

Every parser receives a repository path and produces a list of CodeEntity objects
that represent the architectural elements found in that repository. The CodeEntity
objects are then fed into the graph builder to construct the architecture graph.

Design principle: Parsers are stateless after construction. All state is held in
the CodeEntity objects returned by parse(). This enables parallel parsing of
multiple repositories.

See docs/design/01-code-graph-extraction.md for the full design rationale.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.graph.models import (
        CacheNode,
        CodeEntity,
        DependencyEdge,
        EndpointNode,
        MessageTopicNode,
        ModelNode,
    )


class BaseParser(ABC):
    """
    Abstract base class for all language-specific code parsers.

    Subclasses implement parsing logic for a specific language (Java, Dart, TypeScript).
    All parsers produce the same unified intermediate representation: List[CodeEntity].

    Usage:
        parser = JavaParser()
        entities = parser.parse("/path/to/java/repo")
        endpoints = parser.extract_endpoints()
        models = parser.extract_models()
    """

    def __init__(self) -> None:
        # Internal state populated during parse()
        self._repo_path: str | None = None
        self._parsed_entities: list[CodeEntity] = []

    @property
    def language(self) -> str:
        """Return the language identifier for this parser (e.g., 'java')."""
        raise NotImplementedError

    @abstractmethod
    def parse(self, repo_path: str) -> list["CodeEntity"]:
        """
        Parse an entire repository and return all discovered CodeEntity objects.

        This is the primary entry point for parser execution. It should:
        1. Scan the repository for files of the appropriate language
        2. Parse each file to extract architectural entities
        3. Resolve cross-file relationships where possible
        4. Return a flat list of all discovered CodeEntity objects

        The graph builder (src/graph/builder.py) is responsible for constructing
        edges between entities — parsers only need to identify entities and their
        direct relationships within a single file or class.

        Args:
            repo_path: Absolute path to the root of the repository to analyze.

        Returns:
            List of CodeEntity objects representing all discovered architectural
            elements in the repository.
        """
        ...

    @abstractmethod
    def extract_endpoints(self) -> list["EndpointNode"]:
        """
        Extract API endpoint definitions from the parsed repository.

        Must be called after parse(). Returns all HTTP endpoints (REST controllers,
        route definitions, etc.) discovered in the repository.

        Returns:
            List of EndpointNode objects, each representing one HTTP endpoint.
        """
        ...

    @abstractmethod
    def extract_models(self) -> list["ModelNode"]:
        """
        Extract data model definitions from the parsed repository.

        Includes: DTOs, request/response classes, Dart models, TypeScript interfaces,
        JPA entities, etc. These are the data contracts flowing through the system.

        Returns:
            List of ModelNode objects, each representing one data model/class.
        """
        ...

    @abstractmethod
    def extract_dependencies(self) -> list["DependencyEdge"]:
        """
        Extract declared dependencies between entities in the parsed repository.

        Includes: Feign client declarations, HTTP client calls, import relationships,
        service injections. These become edges in the architecture graph.

        Returns:
            List of DependencyEdge objects representing inter-entity relationships.
        """
        ...

    @abstractmethod
    def extract_cache_usage(self) -> list["CacheNode"]:
        """
        Extract cache usage patterns from the parsed repository.

        Includes: @Cacheable annotations, RedisTemplate usage, cache key patterns,
        TTL declarations. These are used to model cache invalidation impact.

        Returns:
            List of CacheNode objects representing cache usage points.
        """
        ...

    @abstractmethod
    def extract_messaging(self) -> list["MessageTopicNode"]:
        """
        Extract messaging (Kafka) usage from the parsed repository.

        Includes: @KafkaListener declarations, KafkaTemplate.send() calls,
        topic name constants. These model async communication channels.

        Returns:
            List of MessageTopicNode objects representing Kafka topic interactions.
        """
        ...

    def _scan_files(self, repo_path: str, extensions: list[str]) -> list[Path]:
        """
        Utility method to recursively find all files with given extensions.

        Args:
            repo_path: Root directory to scan.
            extensions: List of file extensions to include (e.g., [".java"]).

        Returns:
            Sorted list of Path objects for all matching files.
        """
        root = Path(repo_path)
        files: list[Path] = []
        for ext in extensions:
            files.extend(root.rglob(f"*{ext}"))
        return sorted(files)

    def _read_file(self, file_path: Path) -> str | None:
        """
        Safely read a file's contents, returning None on error.

        Args:
            file_path: Path to the file to read.

        Returns:
            File contents as a string, or None if the file could not be read.
        """
        try:
            return file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return None
