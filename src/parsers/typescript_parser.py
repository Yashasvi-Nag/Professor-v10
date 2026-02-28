"""
TypeScript / Angular parser for Professor v10.

Extracts architectural entities from TypeScript source files, focusing on:
- Angular components (@Component decorator)
- Angular services (@Injectable decorator) and their HTTP calls
- TypeScript interfaces and type aliases (data models/contracts)
- Angular route declarations (RouterModule)
- HTTP client usage patterns (HttpClient.get/post)
- NgModule structure and imports

Detection strategy (Phase 1):
- Regex-based decorator and class signature detection
- Pattern matching for Angular idioms and TypeScript interfaces
- tsconfig.json / angular.json scanning for project structure

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
    SourceLocation,
)
from src.parsers.base import BaseParser


class TypeScriptParser(BaseParser):
    """
    Parser for TypeScript/Angular repositories.

    Scans .ts files and extracts Angular architectural entities using
    decorator-based detection and TypeScript interface parsing.
    """

    @property
    def language(self) -> str:
        return "typescript"

    def parse(self, repo_path: str) -> list[CodeEntity]:
        """
        Parse a TypeScript/Angular repository and extract all architectural entities.

        Scans all .ts files (excluding .spec.ts test files and generated .d.ts files)
        in the repository.

        Args:
            repo_path: Absolute path to the Angular repository root.

        Returns:
            Flat list of all CodeEntity objects found in the repository.
        """
        self._repo_path = repo_path
        self._parsed_entities = []

        ts_files = self._scan_files(repo_path, [".ts"])

        for file_path in ts_files:
            # Skip test files and type declaration files
            if self._is_test_or_declaration_file(file_path):
                continue

            content = self._read_file(file_path)
            if content is None:
                continue

            entities = self._parse_ts_file(file_path, content)
            self._parsed_entities.extend(entities)

        return self._parsed_entities

    def extract_endpoints(self) -> list[EndpointNode]:
        """
        Extract API call patterns from parsed TypeScript files.

        Returns EndpointNode objects for each distinct HTTP call made via
        Angular's HttpClient service.

        Returns:
            List of EndpointNode objects representing backend API calls.
        """
        return [e for e in self._parsed_entities if isinstance(e, EndpointNode)]

    def extract_models(self) -> list[ModelNode]:
        """
        Extract TypeScript interface and type alias definitions.

        These are the frontend data contracts that must stay in sync with
        backend Java DTOs (see docs/design/02-cross-language-schema-alignment.md).

        Returns:
            List of ModelNode objects representing TypeScript data models.
        """
        return [e for e in self._parsed_entities if isinstance(e, ModelNode)]

    def extract_dependencies(self) -> list[DependencyEdge]:
        """
        Extract service-to-backend dependencies declared in TypeScript files.

        Includes: HttpClient calls with extracted URLs, which become edges
        in the architecture graph connecting the Angular frontend to backend APIs.

        Returns:
            List of DependencyEdge objects representing frontend→backend dependencies.
        """
        return []

    def extract_cache_usage(self) -> list[CacheNode]:
        """
        Extract client-side storage patterns from TypeScript files.

        Detects: localStorage, sessionStorage, IndexedDB usage patterns.
        These are client-side caches distinct from server-side Redis caches.

        Returns:
            List of CacheNode objects representing client-side storage usage.
        """
        return [e for e in self._parsed_entities if isinstance(e, CacheNode)]

    def extract_messaging(self) -> list[MessageTopicNode]:
        """
        Extract WebSocket or server-sent event patterns from TypeScript files.

        In Angular apps, this covers WebSocket connections or real-time
        data streams that connect to backend messaging infrastructure.

        Returns:
            List of MessageTopicNode objects representing real-time connections.
        """
        return [e for e in self._parsed_entities if isinstance(e, MessageTopicNode)]

    # -------------------------------------------------------------------------
    # Private parsing methods
    # -------------------------------------------------------------------------

    def _parse_ts_file(self, file_path: Path, content: str) -> list[CodeEntity]:
        """
        Parse a single TypeScript file and extract all entities.

        Args:
            file_path: Path to the .ts file.
            content: File contents as a string.

        Returns:
            List of CodeEntity objects extracted from this file.
        """
        entities: list[CodeEntity] = []
        lines = content.splitlines()
        repo_name = self._infer_repo_name()

        # TODO: Implement full TypeScript/Angular file parsing
        # The implementation should perform the following steps:
        #
        # 1. Detect Angular components:
        #    - @Component({ selector: '...', templateUrl: '...' }) decorator
        #      → ServiceNode with entity_type=EntityType.COMPONENT
        #    - Extract selector, templateUrl, styleUrls from decorator metadata
        #    - Note: components that inject services reveal dependency relationships
        #
        # 2. Detect Angular services (@Injectable):
        #    - @Injectable({ providedIn: 'root' }) → ServiceNode (singleton service)
        #    - Look for HttpClient injection in constructor → this service makes HTTP calls
        #    - Extract HTTP calls: this.http.get<T>('/api/...'), this.http.post<T>(...)
        #      → EndpointNode for each unique URL pattern
        #    - Extract the generic type parameter T → links to a ModelNode (the DTO)
        #
        # 3. Detect TypeScript interfaces and type aliases:
        #    - export interface CouponDto { ... } → ModelNode
        #    - export type CouponResponse = { ... } → ModelNode
        #    - Extract all fields with their types for schema alignment
        #    - Naming patterns: *Dto, *Model, *Response, *Request, *Interface → ModelNode
        #
        # 4. Detect Angular route declarations:
        #    - RouterModule.forRoot(routes) / RouterModule.forChild(routes) → parse routes array
        #    - Route objects: { path: 'coupons', component: CouponListComponent }
        #      → EndpointNode (route) with path and component name
        #    - Lazy-loaded routes: loadChildren: () => import('...') → note the lazy module
        #
        # 5. Detect NgModule imports:
        #    - @NgModule({ imports: [...], declarations: [...] })
        #    - HttpClientModule in imports → confirms this module makes HTTP calls
        #    - Module import graph builds the Angular app's dependency structure
        #
        # 6. Detect localStorage/sessionStorage usage:
        #    - localStorage.setItem('key', ...) / localStorage.getItem('key')
        #      → CacheNode with key name
        #
        # 7. For each detected entity, create a CodeEntity with:
        #    - source_location pointing to the decorator or declaration line
        #    - repo set to repo_name
        #    - language set to Language.TYPESCRIPT
        #
        # See: docs/design/01-code-graph-extraction.md for entity types and
        # docs/design/02-cross-language-schema-alignment.md for TS↔Java alignment.

        # Placeholder: detect interfaces as a minimal example
        for line_num, line in enumerate(lines, start=1):
            interface_match = re.match(r"^export\s+interface\s+(\w+)", line)
            if interface_match:
                interface_name = interface_match.group(1)
                entities.append(
                    ModelNode(
                        id=f"{repo_name}/typescript/interface/{interface_name}",
                        name=interface_name,
                        entity_type=EntityType.MODEL,
                        language=Language.TYPESCRIPT,
                        file_path=str(file_path),
                        line_number=line_num,
                        repo=repo_name,
                        metadata={"kind": "interface"},
                    )
                )

        return entities

    def _extract_decorator_metadata(self, content: str, decorator: str) -> list[dict]:
        """
        Extract metadata from Angular decorators.

        Parses the JSON-like object literal passed to a decorator, e.g.:
        @Component({ selector: 'app-root', templateUrl: './app.component.html' })

        Args:
            content: Full file content to search within.
            decorator: Decorator name without @ (e.g., "Component", "Injectable").

        Returns:
            List of dicts, one per occurrence of the decorator, with metadata key-value pairs.
        """
        # TODO: Implement decorator metadata extraction
        # Should handle:
        # - Single-line decorators: @Injectable({ providedIn: 'root' })
        # - Multi-line decorators spanning several lines
        # - Nested objects in decorator metadata
        # - Template literals and dynamic values
        return []

    def _extract_http_calls(self, content: str, file_path: Path) -> list[EndpointNode]:
        """
        Extract HttpClient call patterns from a TypeScript service file.

        Identifies patterns like:
        - this.http.get<CouponDto[]>('/api/coupons')
        - this.http.post<OrderResponse>(`/api/orders/${userId}`, body)
        - this.http.put<void>(this.baseUrl + '/api/users/' + id, data)

        Args:
            content: TypeScript file content.
            file_path: Path to the file (for source location).

        Returns:
            List of EndpointNode objects, one per HTTP call pattern found.
        """
        # TODO: Implement HTTP call extraction
        # For each call, extract:
        # - HTTP method (get, post, put, delete, patch)
        # - URL pattern (static string, template literal, or concatenation)
        # - Generic type parameter (the expected response DTO type)
        # These become EndpointNode objects AND DependencyEdge objects
        # linking this Angular service to the backend API.
        return []

    def _is_test_or_declaration_file(self, file_path: Path) -> bool:
        """
        Detect test files (.spec.ts) and type declaration files (.d.ts).

        These files should be excluded from architectural analysis:
        - .spec.ts: Angular test files
        - .d.ts: TypeScript type declarations (usually from node_modules or generated)

        Args:
            file_path: Path to the file.

        Returns:
            True if the file should be excluded.
        """
        name = file_path.name
        return name.endswith(".spec.ts") or name.endswith(".d.ts")

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
