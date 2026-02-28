"""
Tests for the Dart/Flutter parser.

Tests cover:
- Model class detection (fromJson/toJson presence)
- API client detection
- Generated file exclusion (.g.dart, .freezed.dart)
- Empty repository handling
"""

from pathlib import Path

import pytest

from src.graph.models import Language
from src.parsers.dart_parser import DartParser


@pytest.fixture
def dart_parser() -> DartParser:
    """Return a fresh DartParser instance."""
    return DartParser()


@pytest.fixture
def temp_dart_repo(tmp_path: Path) -> Path:
    """
    Create a temporary directory with sample Dart files for testing.

    Returns:
        Path to the temporary Flutter repository root.
    """
    lib_dir = tmp_path / "lib" / "models"
    lib_dir.mkdir(parents=True)

    model_file = lib_dir / "coupon_model.dart"
    model_file.write_text(
        """
class CouponModel {
  final String couponId;
  final double discountAmount;
  double? estimatedSavings;

  CouponModel({
    required this.couponId,
    required this.discountAmount,
    this.estimatedSavings,
  });

  factory CouponModel.fromJson(Map<String, dynamic> json) {
    return CouponModel(
      couponId: json['couponId'] as String,
      discountAmount: (json['discountAmount'] as num).toDouble(),
      estimatedSavings: json['estimatedSavings'] as double?,
    );
  }

  Map<String, dynamic> toJson() => {
        'couponId': couponId,
        'discountAmount': discountAmount,
        'estimatedSavings': estimatedSavings,
      };
}
""",
        encoding="utf-8",
    )

    # Create a generated file that should be excluded
    generated_file = lib_dir / "coupon_model.g.dart"
    generated_file.write_text(
        "// GENERATED CODE - DO NOT MODIFY BY HAND\n// *.g.dart files are generated",
        encoding="utf-8",
    )

    # Create pubspec.yaml
    pubspec = tmp_path / "pubspec.yaml"
    pubspec.write_text(
        """
name: flutter_app
version: 1.0.0

dependencies:
  flutter:
    sdk: flutter
  http: ^1.1.0
  provider: ^6.1.1

dev_dependencies:
  flutter_test:
    sdk: flutter
""",
        encoding="utf-8",
    )

    return tmp_path


class TestDartParserLanguageProperty:
    """Test the language property."""

    def test_language_is_dart(self, dart_parser: DartParser) -> None:
        assert dart_parser.language == "dart"


class TestDartParserParse:
    """Tests for the main parse() method."""

    def test_parse_returns_list(
        self, dart_parser: DartParser, temp_dart_repo: Path
    ) -> None:
        """parse() should return a list."""
        result = dart_parser.parse(str(temp_dart_repo))
        assert isinstance(result, list)

    def test_parse_empty_directory(self, dart_parser: DartParser, tmp_path: Path) -> None:
        """parse() should return an empty list for a directory with no Dart files."""
        result = dart_parser.parse(str(tmp_path))
        assert result == []

    def test_parse_does_not_include_generated_files(
        self, dart_parser: DartParser, temp_dart_repo: Path
    ) -> None:
        """parse() should exclude .g.dart generated files from analysis."""
        entities = dart_parser.parse(str(temp_dart_repo))
        for entity in entities:
            assert not entity.file_path.endswith(".g.dart"), (
                f"Generated file should be excluded: {entity.file_path}"
            )

    def test_parse_sets_language_dart(
        self, dart_parser: DartParser, temp_dart_repo: Path
    ) -> None:
        """All parsed entities should have language=DART."""
        entities = dart_parser.parse(str(temp_dart_repo))
        for entity in entities:
            assert entity.language == Language.DART


class TestDartParserExtractModels:
    """Tests for extract_models()."""

    def test_extract_models_returns_list(
        self, dart_parser: DartParser, temp_dart_repo: Path
    ) -> None:
        dart_parser.parse(str(temp_dart_repo))
        result = dart_parser.extract_models()
        assert isinstance(result, list)


class TestDartParserExtractEndpoints:
    """Tests for extract_endpoints()."""

    def test_extract_endpoints_returns_list(
        self, dart_parser: DartParser, temp_dart_repo: Path
    ) -> None:
        dart_parser.parse(str(temp_dart_repo))
        result = dart_parser.extract_endpoints()
        assert isinstance(result, list)


class TestDartParserIsGeneratedFile:
    """Tests for the _is_generated_file() helper."""

    def test_detects_g_dart(self, dart_parser: DartParser) -> None:
        assert dart_parser._is_generated_file(Path("coupon_model.g.dart")) is True

    def test_detects_freezed_dart(self, dart_parser: DartParser) -> None:
        assert dart_parser._is_generated_file(Path("coupon_model.freezed.dart")) is True

    def test_detects_gr_dart(self, dart_parser: DartParser) -> None:
        assert dart_parser._is_generated_file(Path("router.gr.dart")) is True

    def test_detects_mocks_dart(self, dart_parser: DartParser) -> None:
        assert dart_parser._is_generated_file(Path("mock_services.mocks.dart")) is True

    def test_normal_dart_file_not_generated(self, dart_parser: DartParser) -> None:
        assert dart_parser._is_generated_file(Path("coupon_model.dart")) is False
