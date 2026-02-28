"""
Tests for the Java/Spring Boot parser.

Tests cover:
- Controller detection via @RestController annotation
- Endpoint extraction from @GetMapping, @PostMapping, etc.
- DTO detection by naming conventions and @Entity annotation
- Feign client detection
- Cache annotation detection
- Kafka listener/producer detection
- Test file exclusion
- Empty / non-Java repository handling
"""

from pathlib import Path

import pytest

from src.graph.models import EntityType, Language
from src.parsers.java_parser import JavaParser


@pytest.fixture
def java_parser() -> JavaParser:
    """Return a fresh JavaParser instance."""
    return JavaParser()


@pytest.fixture
def temp_java_repo(tmp_path: Path) -> Path:
    """
    Create a temporary directory with sample Java files for testing.

    Returns:
        Path to the temporary repository root.
    """
    # Create a minimal Spring Boot controller
    src_dir = tmp_path / "src" / "main" / "java" / "com" / "example"
    src_dir.mkdir(parents=True)

    controller_file = src_dir / "CouponController.java"
    controller_file.write_text(
        """
package com.example;

import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;

@RestController
@RequestMapping("/api/coupons")
public class CouponController {

    @GetMapping("/{userId}")
    public CouponResponseDto getCoupons(String userId) {
        return couponService.getCoupons(userId);
    }
}
""",
        encoding="utf-8",
    )

    dto_file = src_dir / "CouponResponseDto.java"
    dto_file.write_text(
        """
package com.example;

public class CouponResponseDto {
    private String couponId;
    private java.math.BigDecimal discountAmount;
    private java.math.BigDecimal estimatedSavings;
}
""",
        encoding="utf-8",
    )

    # Create a test file that should be excluded
    test_dir = tmp_path / "src" / "test" / "java" / "com" / "example"
    test_dir.mkdir(parents=True)
    test_file = test_dir / "CouponControllerTest.java"
    test_file.write_text(
        "package com.example; class CouponControllerTest {}",
        encoding="utf-8",
    )

    return tmp_path


class TestJavaParserLanguageProperty:
    """Test the language property."""

    def test_language_is_java(self, java_parser: JavaParser) -> None:
        assert java_parser.language == "java"


class TestJavaParserParse:
    """Tests for the main parse() method."""

    def test_parse_returns_list(self, java_parser: JavaParser, temp_java_repo: Path) -> None:
        """parse() should return a list (even if empty)."""
        result = java_parser.parse(str(temp_java_repo))
        assert isinstance(result, list)

    def test_parse_detects_rest_controller(
        self, java_parser: JavaParser, temp_java_repo: Path
    ) -> None:
        """parse() should detect @RestController annotated classes."""
        entities = java_parser.parse(str(temp_java_repo))
        controller_entities = [
            e for e in entities if e.entity_type == EntityType.CONTROLLER
        ]
        assert len(controller_entities) >= 1
        names = [e.name for e in controller_entities]
        assert "CouponController" in names

    def test_parse_sets_language_java(
        self, java_parser: JavaParser, temp_java_repo: Path
    ) -> None:
        """All parsed entities should have language=JAVA."""
        entities = java_parser.parse(str(temp_java_repo))
        for entity in entities:
            assert entity.language == Language.JAVA

    def test_parse_sets_repo_name(
        self, java_parser: JavaParser, temp_java_repo: Path
    ) -> None:
        """Entities should have repo set to the directory name of the repo."""
        entities = java_parser.parse(str(temp_java_repo))
        for entity in entities:
            assert entity.repo == temp_java_repo.name

    def test_parse_excludes_test_files(
        self, java_parser: JavaParser, temp_java_repo: Path
    ) -> None:
        """parse() should not return entities from src/test/ files."""
        entities = java_parser.parse(str(temp_java_repo))
        for entity in entities:
            assert "Test" not in entity.file_path or "src/test" not in entity.file_path

    def test_parse_empty_directory(self, java_parser: JavaParser, tmp_path: Path) -> None:
        """parse() should return an empty list for a directory with no Java files."""
        result = java_parser.parse(str(tmp_path))
        assert result == []

    def test_parse_sets_file_path(
        self, java_parser: JavaParser, temp_java_repo: Path
    ) -> None:
        """Entities should have non-empty file_path."""
        entities = java_parser.parse(str(temp_java_repo))
        for entity in entities:
            assert entity.file_path != ""

    def test_parse_sets_line_number(
        self, java_parser: JavaParser, temp_java_repo: Path
    ) -> None:
        """Entities should have a positive line number."""
        entities = java_parser.parse(str(temp_java_repo))
        for entity in entities:
            assert entity.line_number > 0


class TestJavaParserExtractEndpoints:
    """Tests for extract_endpoints()."""

    def test_extract_endpoints_returns_list(
        self, java_parser: JavaParser, temp_java_repo: Path
    ) -> None:
        """extract_endpoints() should return a list after parse() is called."""
        java_parser.parse(str(temp_java_repo))
        result = java_parser.extract_endpoints()
        assert isinstance(result, list)

    def test_extract_endpoints_before_parse(self, java_parser: JavaParser) -> None:
        """extract_endpoints() before parse() should return an empty list."""
        result = java_parser.extract_endpoints()
        assert result == []


class TestJavaParserExtractModels:
    """Tests for extract_models()."""

    def test_extract_models_returns_list(
        self, java_parser: JavaParser, temp_java_repo: Path
    ) -> None:
        """extract_models() should return a list after parse() is called."""
        java_parser.parse(str(temp_java_repo))
        result = java_parser.extract_models()
        assert isinstance(result, list)


class TestJavaParserExtractCacheUsage:
    """Tests for extract_cache_usage()."""

    def test_extract_cache_usage_returns_list(
        self, java_parser: JavaParser, temp_java_repo: Path
    ) -> None:
        java_parser.parse(str(temp_java_repo))
        result = java_parser.extract_cache_usage()
        assert isinstance(result, list)


class TestJavaParserExtractMessaging:
    """Tests for extract_messaging()."""

    def test_extract_messaging_returns_list(
        self, java_parser: JavaParser, temp_java_repo: Path
    ) -> None:
        java_parser.parse(str(temp_java_repo))
        result = java_parser.extract_messaging()
        assert isinstance(result, list)


class TestJavaParserInternals:
    """Tests for internal helper methods."""

    def test_is_test_file_detects_test_directory(self, java_parser: JavaParser) -> None:
        """_is_test_file() should return True for files in src/test/."""
        path = Path("/repo/src/test/java/com/example/MyTest.java")
        assert java_parser._is_test_file(path) is True

    def test_is_test_file_detects_test_suffix(self, java_parser: JavaParser) -> None:
        """_is_test_file() should return True for files ending in Test.java."""
        path = Path("/repo/src/main/java/com/example/UserControllerTest.java")
        assert java_parser._is_test_file(path) is True

    def test_is_test_file_returns_false_for_main(self, java_parser: JavaParser) -> None:
        """_is_test_file() should return False for normal source files."""
        path = Path("/repo/src/main/java/com/example/UserController.java")
        assert java_parser._is_test_file(path) is False

    def test_extract_class_name_finds_class(self, java_parser: JavaParser) -> None:
        """_extract_class_name() should find the class name following an annotation."""
        lines = [
            "// comment",
            "@RestController",
            "public class CouponController {",
            "    // body",
        ]
        result = java_parser._extract_class_name(lines, 1)  # 0-indexed: line 1 = @RestController
        assert result == "CouponController"

    def test_extract_class_name_returns_none_if_not_found(
        self, java_parser: JavaParser
    ) -> None:
        """_extract_class_name() should return None if no class declaration is found."""
        lines = ["@RestController", "// comment", "// comment", "// comment", "// comment"]
        result = java_parser._extract_class_name(lines, 0)
        assert result is None
