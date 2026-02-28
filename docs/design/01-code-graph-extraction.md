# Code Graph Extraction

## Status

Draft — Phase 1 Scaffold

---

## 1. Problem

Large enterprise codebases spanning multiple repositories and languages have **no unified structural representation**. Each repository is a silo:

- Java Spring Boot services define controllers, DTOs, Feign clients, Kafka listeners, JPA entities
- Dart Flutter apps consume APIs, manage state, define models
- TypeScript Angular apps call HTTP endpoints, define interfaces, handle routing

Without extracting these into a shared representation, it is impossible to:
- Understand cross-service dependencies
- Identify all artifacts affected by a change
- Validate contract consistency across language boundaries

---

## 2. Approach

### Parser Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                      Parser Pipeline                            │
│                                                                 │
│  Multi-Repo Source Code                                         │
│         │                                                       │
│         ▼                                                       │
│  ┌─────────────────┐                                            │
│  │ Repo Ingestion  │ ── Discovers repos, detects languages,     │
│  └────────┬────────┘    resolves project structure              │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────┐                                            │
│  │ Language        │ ── Routes each file to appropriate parser  │
│  │ Detection       │                                            │
│  └────────┬────────┘                                            │
│           │                                                     │
│           ▼                                                     │
│  ┌──────────────────────────────────────┐                       │
│  │         Language-Specific Parsers    │                       │
│  │                                      │                       │
│  │  JavaParser  DartParser  TSParser    │                       │
│  └──────────────────┬───────────────────┘                       │
│                     │                                           │
│                     ▼                                           │
│  ┌─────────────────────────────────────┐                        │
│  │   Entity Extraction                 │                        │
│  │   (controllers, models, services,   │                        │
│  │    clients, topics, caches, repos)  │                        │
│  └──────────────┬──────────────────────┘                        │
│                 │                                               │
│                 ▼                                               │
│  ┌──────────────────────────────┐                               │
│  │   Graph Construction         │                               │
│  │   (nodes + edges)            │                               │
│  └──────────────────────────────┘                               │
└─────────────────────────────────────────────────────────────────┘
```

### Static Analysis Strategy

Phase 1 uses **regex + simple AST heuristics** as the baseline approach. Regex is used for annotation detection, import scanning, and class/method signature extraction. For deeper analysis, tree-sitter will be integrated (see ADR 004).

---

## 3. What to Extract

### Java / Spring Boot

| Entity Type | Detection Strategy | Example |
|---|---|---|
| REST Controllers | `@RestController`, `@Controller` annotations | `UserController` |
| Endpoints | `@GetMapping`, `@PostMapping`, etc. | `GET /api/users/{id}` |
| DTOs | Classes in `dto/` packages or `*Dto`, `*Request`, `*Response` naming | `UserResponseDto` |
| Service Classes | `@Service` annotation | `UserService` |
| Feign Clients | `@FeignClient` annotation | `CouponServiceClient` |
| JPA Entities | `@Entity`, `@Table` annotations | `UserEntity` |
| Repositories | `@Repository` or `extends JpaRepository` | `UserRepository` |
| Kafka Producers | `KafkaTemplate.send()`, `@KafkaListener` | `UserEventProducer` |
| Kafka Consumers | `@KafkaListener` annotation | `OrderEventListener` |
| Cache Usage | `@Cacheable`, `@CacheEvict`, `RedisTemplate` | `getUserById` |
| Feature Flags | Custom `@FeatureFlag` or config-based flags | `ESTIMATIONS_ENABLED` |
| Config Properties | `@ConfigurationProperties` | `AppConfig` |

### Dart / Flutter

| Entity Type | Detection Strategy | Example |
|---|---|---|
| API Client Calls | `http.get/post`, `Dio` calls | `getCoupons()` |
| Model Classes | `fromJson`/`toJson` presence, `class *Model` | `CouponModel` |
| State Management | `Provider`, `Riverpod`, `Bloc` patterns | `CouponProvider` |
| Routes | `Navigator.pushNamed`, route maps | `/coupon-detail` |
| Dependencies | `pubspec.yaml` | `http: ^1.1.0` |

### TypeScript / Angular

| Entity Type | Detection Strategy | Example |
|---|---|---|
| Components | `@Component` decorator | `CouponListComponent` |
| Services | `@Injectable` decorator | `CouponApiService` |
| Interfaces/Models | `interface *`, `type *` | `CouponDto` |
| HTTP Calls | `HttpClient.get/post` | `getCoupons()` |
| Routes | `RouterModule.forRoot/forChild` | `/admin/coupons` |
| Module Imports | `imports: []` in `@NgModule` | `HttpClientModule` |

---

## 4. Output: Unified Architecture Graph

After parsing, all extracted entities are converted into a unified graph:

### Node Types

```python
# Every node has at minimum:
{
    "id": "unique-id",
    "name": "EntityName",
    "type": "CONTROLLER|ENDPOINT|DTO|SERVICE|...",
    "language": "java|dart|typescript",
    "file_path": "path/to/file.java",
    "line_number": 42,
    "repo": "repo-name",
    "metadata": {}
}
```

### Edge Types

| Edge | Meaning |
|---|---|
| `CALLS` | Service A calls Service B (Feign/HTTP) |
| `CONSUMES` | Service consumes Kafka topic |
| `PRODUCES` | Service produces to Kafka topic |
| `USES_CACHE` | Service reads/writes cache key |
| `READS_DB` | Service/repo reads database table |
| `WRITES_DB` | Service/repo writes database table |
| `MAPS_TO` | Java DTO maps to Dart model or TS interface |
| `DEPENDS_ON` | Generic structural dependency |
| `EXPOSES` | Controller exposes an endpoint |
| `IMPLEMENTS` | Service implements a contract/interface |

---

## 5. Parser Interface

All parsers implement a common abstract interface (see `src/parsers/base.py`):

```python
class BaseParser:
    def parse(self, repo_path: str) -> list[CodeEntity]: ...
    def extract_endpoints(self) -> list[EndpointNode]: ...
    def extract_models(self) -> list[ModelNode]: ...
    def extract_dependencies(self) -> list[DependencyEdge]: ...
    def extract_cache_usage(self) -> list[CacheNode]: ...
    def extract_messaging(self) -> list[MessageTopicNode]: ...
```

---

## 6. Implementation Notes

- Start with regex-based detection for annotations and naming conventions (fast, ~80% coverage)
- Layer tree-sitter AST parsing for precise extraction (handles edge cases)
- Parser output is language-agnostic `CodeEntity` objects (unified intermediate representation)
- Each `CodeEntity` carries a `source_location` (file, line) for evidence linking
- Parsers are stateless; the graph builder assembles relationships
