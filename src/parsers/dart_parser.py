"""
Dart / Flutter parser for Professor v10.

Extracts architectural entities from Dart source files, focusing on:
- Model classes with fromJson/toJson methods (API contracts)
- API client classes and their HTTP calls (service consumers)
- State management patterns (Provider, Riverpod, Bloc/Cubit)
- Route declarations and navigation patterns
- pubspec.yaml dependency declarations

Detection strategy (Phase 1):
- Regex-based class and method signature detection
- Pattern matching for common Flutter/Dart idioms
- pubspec.yaml YAML parsing for dependency declarations

See docs/design/01-code-graph-extraction.md for full design rationale.
"""

from pathlib import Path

from src.graph.models import (
    CacheNode,
    CodeEntity,
    DependencyEdge,
    EndpointNode,
    MessageTopicNode,
    ModelNode,
    SourceLocation,
)
from src.parsers.base import BaseParser


class DartParser(BaseParser):
    """
    Parser for Dart/Flutter repositories.

    Scans .dart files and pubspec.yaml to extract Flutter architectural entities
    using pattern-based detection heuristics.
    """

    @property
    def language(self) -> str:
        return "dart"

    def parse(self, repo_path: str) -> list[CodeEntity]:
        """
        Parse a Dart/Flutter repository and extract all architectural entities.

        Scans all .dart files and pubspec.yaml in the repository.

        Args:
            repo_path: Absolute path to the Flutter repository root.

        Returns:
            Flat list of all CodeEntity objects found in the repository.
        """
        self._repo_path = repo_path
        self._parsed_entities = []

        dart_files = self._scan_files(repo_path, [".dart"])

        for file_path in dart_files:
            # Skip generated files (*.g.dart, *.freezed.dart)
            if self._is_generated_file(file_path):
                continue

            content = self._read_file(file_path)
            if content is None:
                continue

            entities = self._parse_dart_file(file_path, content)
            self._parsed_entities.extend(entities)

        # Also parse pubspec.yaml for package dependencies
        pubspec_entities = self._parse_pubspec(repo_path)
        self._parsed_entities.extend(pubspec_entities)

        return self._parsed_entities

    def extract_endpoints(self) -> list[EndpointNode]:
        """
        Extract API call patterns from parsed Dart files.

        In Dart/Flutter, "endpoints" are the API calls made to backend services.
        Returns EndpointNode objects representing each distinct API call pattern.

        Returns:
            List of EndpointNode objects representing API calls made by the app.
        """
        return [e for e in self._parsed_entities if isinstance(e, EndpointNode)]

    def extract_models(self) -> list[ModelNode]:
        """
        Extract Dart model class definitions from parsed files.

        Identifies classes with fromJson/toJson methods, which are the data models
        that map to backend API response DTOs.

        Returns:
            List of ModelNode objects representing Dart data models.
        """
        return [e for e in self._parsed_entities if isinstance(e, ModelNode)]

    def extract_dependencies(self) -> list[DependencyEdge]:
        """
        Extract service dependencies declared in the Dart code.

        Includes: API client classes that make HTTP calls to backend services.

        Returns:
            List of DependencyEdge objects representing declared API dependencies.
        """
        return []

    def extract_cache_usage(self) -> list[CacheNode]:
        """
        Extract local storage and caching patterns from Dart files.

        Detects: shared_preferences, hive, flutter_secure_storage usage.
        Note: These are client-side caches, distinct from server-side Redis caches.

        Returns:
            List of CacheNode objects representing client-side cache usage.
        """
        return [e for e in self._parsed_entities if isinstance(e, CacheNode)]

    def extract_messaging(self) -> list[MessageTopicNode]:
        """
        Extract messaging patterns from Dart files.

        In Flutter apps, this primarily covers Firebase messaging or WebSocket
        connections. Kafka is not typically used directly from Flutter.

        Returns:
            List of MessageTopicNode objects (usually empty for Flutter apps).
        """
        return [e for e in self._parsed_entities if isinstance(e, MessageTopicNode)]

    # -------------------------------------------------------------------------
    # Private parsing methods
    # -------------------------------------------------------------------------

    def _parse_dart_file(self, file_path: Path, content: str) -> list[CodeEntity]:
        """
        Parse a single Dart file and extract all entities.

        Args:
            file_path: Path to the .dart file.
            content: File contents as a string.

        Returns:
            List of CodeEntity objects extracted from this file.
        """
        entities: list[CodeEntity] = []
        lines = content.splitlines()  # noqa: F841  (used by TODO implementation)
        repo_name = self._infer_repo_name()  # noqa: F841  (used by TODO implementation)

        # TODO: Implement full Dart file parsing
        # The implementation should perform the following steps:
        #
        # 1. Detect model classes:
        #    - Classes with fromJson(Map<String, dynamic> json) factory constructor
        #      → ModelNode with fields extracted from the constructor body
        #    - Classes with toJson() method → ModelNode
        #    - Naming conventions: *Model, *Dto, *Response, *Entity → ModelNode
        #    - @freezed annotation → ModelNode (Freezed union types)
        #
        # 2. Detect API client classes:
        #    - Classes with http.get(), http.post(), dio.get(), dio.post() calls
        #      → EndpointNode with the URL extracted from the call
        #    - Classes in api/ or services/ directories with HTTP calls
        #    - Retrofit-style annotations (@GET, @POST) if using Retrofit for Dart
        #
        # 3. Detect state management patterns:
        #    - extends ChangeNotifier → ServiceNode (Provider pattern)
        #    - extends StateNotifier → ServiceNode (Riverpod pattern)
        #    - extends Bloc, extends Cubit → ServiceNode (BLoC pattern)
        #    Record the state class name and what model it manages.
        #
        # 4. Detect route declarations:
        #    - GoRouter route definitions → EndpointNode (route path)
        #    - Navigator.pushNamed(context, '/path') → EndpointNode (navigation)
        #    - Route maps: {'/path': (context) => Widget()} → EndpointNode
        #
        # 5. For each detected entity, create a CodeEntity with:
        #    - source_location pointing to the exact class/method declaration line
        #    - repo set to repo_name
        #    - language set to Language.DART
        #
        # Detection priority: explicit class role > naming convention > directory location
        #
        # See: docs/design/01-code-graph-extraction.md for entity types and
        # docs/design/02-cross-language-schema-alignment.md for model alignment.

        return entities

    def _parse_pubspec(self, repo_path: str) -> list[CodeEntity]:
        """
        Parse pubspec.yaml to extract declared package dependencies.

        pubspec.yaml contains the Flutter app's declared dependencies, which
        can indicate what HTTP clients, state management libraries, and
        storage solutions are in use.

        Args:
            repo_path: Root path of the Flutter repository.

        Returns:
            List of CodeEntity objects representing notable package dependencies.
        """
        entities: list[CodeEntity] = []

        # TODO: Implement pubspec.yaml parsing
        # Steps:
        # 1. Find pubspec.yaml in repo_path
        # 2. Parse YAML with PyYAML
        # 3. Extract dependencies and dev_dependencies sections
        # 4. For each notable dependency, create a CodeEntity:
        #    - http, dio → note that HTTP client is in use (affects API detection)
        #    - provider, riverpod, flutter_bloc → note state management library
        #    - shared_preferences, hive, flutter_secure_storage → CacheNode (local storage)
        #    - firebase_messaging → MessageTopicNode

        return entities

    def _is_generated_file(self, file_path: Path) -> bool:
        """
        Detect auto-generated Dart files that should be excluded from analysis.

        Generated files (.g.dart, .freezed.dart, .gr.dart) contain machine-generated
        code that mirrors the source files and should not be parsed as independent entities.

        Args:
            file_path: Path to the Dart file.

        Returns:
            True if the file appears to be auto-generated.
        """
        name = file_path.name
        return (
            name.endswith(".g.dart")
            or name.endswith(".freezed.dart")
            or name.endswith(".gr.dart")
            or name.endswith(".mocks.dart")
        )

    def _infer_repo_name(self) -> str:
        """Infer repository name from the repo path."""
        if self._repo_path:
            return Path(self._repo_path).name
        return "unknown-repo"

    def _build_source_location(self, file_path: Path, line_number: int) -> SourceLocation:
        """Build a SourceLocation for evidence linking."""
        return SourceLocation(
            repo=self._infer_repo_name(),
            file_path=str(file_path),
            line_number=line_number,
        )
