"""
Configuration management for Professor v10.

Uses Pydantic BaseSettings for environment variable and config file support.
Settings can be overridden via environment variables (prefixed with PROFESSOR_)
or via a YAML config file.
"""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class RepoConfig(BaseSettings):
    """Configuration for a single repository to be analyzed."""

    # Human-readable name for the repository (used as a graph node prefix)
    name: str

    # Absolute or relative path to the repository root on the local filesystem
    path: str

    # Primary language of the repository (used to select the correct parser)
    # Supported: "java", "dart", "typescript"
    language: str

    # Optional: sub-path within the repo to start analysis from (e.g., "src/main/java")
    source_root: str | None = None

    # Optional: glob patterns for files to exclude from analysis
    exclude_patterns: list[str] = Field(default_factory=list)


class GraphSettings(BaseSettings):
    """Settings for the architecture graph storage and querying."""

    # Maximum traversal depth for impact analysis (prevents runaway traversal)
    max_traversal_depth: int = Field(default=10, ge=1, le=50)

    # Minimum confidence score for a claim to be included in the output
    # Claims below this threshold are flagged for human review
    min_confidence_threshold: float = Field(default=0.60, ge=0.0, le=1.0)

    # Whether to export the graph to JSON after construction
    export_graph_json: bool = False

    # Path to export the graph JSON (if export_graph_json is True)
    graph_export_path: str | None = None


class ParserSettings(BaseSettings):
    """Settings controlling parser behavior."""

    # Whether to use tree-sitter for precise AST parsing
    # If False, only regex-based heuristics are used (faster but less accurate)
    use_tree_sitter: bool = False

    # Whether to parse test files (files in test/ or *Test.java, etc.)
    include_test_files: bool = False

    # File size limit in KB — files larger than this are skipped with a warning
    max_file_size_kb: int = Field(default=500, ge=1)

    # Whether to follow symlinks when scanning directories
    follow_symlinks: bool = False


class OutputSettings(BaseSettings):
    """Settings for document generation."""

    # Output directory for generated architectural documents
    output_dir: str = "output"

    # Document format: "markdown" (default) or "html" (future)
    output_format: str = "markdown"

    # Whether to include evidence links in the output document
    include_evidence_links: bool = True

    # Whether to include a Trust Summary section in the output document
    include_trust_summary: bool = True

    # Jinja2 template to use for the solution document
    solution_document_template: str = "solution_document.md.j2"


class Settings(BaseSettings):
    """
    Root configuration for Professor v10.

    Reads configuration from environment variables prefixed with PROFESSOR_.
    Example: PROFESSOR_LOG_LEVEL=DEBUG

    For per-run configuration (repo list, output paths), use the YAML config
    file format shown in examples/sample_repo_config.yaml.
    """

    model_config = {"env_prefix": "PROFESSOR_", "env_nested_delimiter": "__"}

    # Logging level
    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")

    # List of repositories to analyze (populated from YAML config at runtime)
    repos: list[RepoConfig] = Field(default_factory=list)

    # Graph settings
    graph: GraphSettings = Field(default_factory=GraphSettings)

    # Parser settings
    parser: ParserSettings = Field(default_factory=ParserSettings)

    # Output settings
    output: OutputSettings = Field(default_factory=OutputSettings)

    @classmethod
    def from_yaml(cls, config_path: str) -> "Settings":
        """
        Load settings from a YAML configuration file.

        The YAML file format is documented in examples/sample_repo_config.yaml.

        Args:
            config_path: Path to the YAML configuration file.

        Returns:
            Settings instance populated from the YAML file.
        """
        import yaml  # noqa: PLC0415

        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(path) as f:
            data = yaml.safe_load(f)

        return cls(**data)
