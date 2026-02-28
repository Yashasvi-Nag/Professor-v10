"""
Parsers package for Professor v10.

Each parser is responsible for extracting CodeEntity objects from source code
in a specific language. All parsers implement the BaseParser interface and
produce a unified intermediate representation.

Supported parsers:
- JavaParser: Java/Spring Boot (src/parsers/java_parser.py)
- DartParser: Dart/Flutter (src/parsers/dart_parser.py)
- TypeScriptParser: TypeScript/Angular (src/parsers/typescript_parser.py)
"""

from src.parsers.base import BaseParser
from src.parsers.dart_parser import DartParser
from src.parsers.java_parser import JavaParser
from src.parsers.typescript_parser import TypeScriptParser

# Registry mapping language identifiers to parser classes.
# To add a new language, implement BaseParser and add an entry here.
PARSER_REGISTRY: dict[str, type[BaseParser]] = {
    "java": JavaParser,
    "dart": DartParser,
    "typescript": TypeScriptParser,
}


def get_parser(language: str) -> BaseParser:
    """
    Instantiate the appropriate parser for the given language.

    Args:
        language: Language identifier string (e.g., "java", "dart", "typescript").

    Returns:
        An instance of the appropriate BaseParser subclass.

    Raises:
        ValueError: If no parser is registered for the given language.
    """
    parser_class = PARSER_REGISTRY.get(language.lower())
    if parser_class is None:
        supported = ", ".join(PARSER_REGISTRY.keys())
        raise ValueError(
            f"No parser registered for language '{language}'. "
            f"Supported languages: {supported}"
        )
    return parser_class()


__all__ = ["BaseParser", "JavaParser", "DartParser", "TypeScriptParser", "get_parser", "PARSER_REGISTRY"]
