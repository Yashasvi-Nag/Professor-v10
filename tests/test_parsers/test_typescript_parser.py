"""
Tests for the TypeScript/Angular parser.

Tests cover:
- Interface detection (export interface ...)
- Component and service detection (@Component, @Injectable)
- Spec file exclusion
- Declaration file (.d.ts) exclusion
- Empty repository handling
"""

from pathlib import Path

import pytest

from src.graph.models import EntityType, Language
from src.parsers.typescript_parser import TypeScriptParser


@pytest.fixture
def ts_parser() -> TypeScriptParser:
    """Return a fresh TypeScriptParser instance."""
    return TypeScriptParser()


@pytest.fixture
def temp_ts_repo(tmp_path: Path) -> Path:
    """
    Create a temporary directory with sample TypeScript/Angular files.

    Returns:
        Path to the temporary Angular repository root.
    """
    src_dir = tmp_path / "src" / "app" / "models"
    src_dir.mkdir(parents=True)

    interface_file = src_dir / "coupon.dto.ts"
    interface_file.write_text(
        """
export interface CouponDto {
  couponId: string;
  discountAmount: number;
  estimatedSavings?: number;
}

export interface CouponListResponse {
  coupons: CouponDto[];
  total: number;
}
""",
        encoding="utf-8",
    )

    service_dir = tmp_path / "src" / "app" / "services"
    service_dir.mkdir(parents=True)

    service_file = service_dir / "coupon-api.service.ts"
    service_file.write_text(
        """
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { CouponDto } from '../models/coupon.dto';

@Injectable({
  providedIn: 'root'
})
export class CouponApiService {
  constructor(private http: HttpClient) {}

  getCoupons(userId: string) {
    return this.http.get<CouponDto[]>(`/api/coupons/${userId}`);
  }
}
""",
        encoding="utf-8",
    )

    # Create a spec file that should be excluded
    spec_file = service_dir / "coupon-api.service.spec.ts"
    spec_file.write_text(
        "describe('CouponApiService', () => { it('should be created', () => {}); });",
        encoding="utf-8",
    )

    # Create a .d.ts declaration file that should be excluded
    types_dir = tmp_path / "node_modules" / "@types"
    types_dir.mkdir(parents=True)
    decl_file = types_dir / "coupon.d.ts"
    decl_file.write_text("declare module 'coupon' {}", encoding="utf-8")

    return tmp_path


class TestTypeScriptParserLanguageProperty:
    """Test the language property."""

    def test_language_is_typescript(self, ts_parser: TypeScriptParser) -> None:
        assert ts_parser.language == "typescript"


class TestTypeScriptParserParse:
    """Tests for the main parse() method."""

    def test_parse_returns_list(
        self, ts_parser: TypeScriptParser, temp_ts_repo: Path
    ) -> None:
        """parse() should return a list."""
        result = ts_parser.parse(str(temp_ts_repo))
        assert isinstance(result, list)

    def test_parse_detects_interfaces(
        self, ts_parser: TypeScriptParser, temp_ts_repo: Path
    ) -> None:
        """parse() should detect exported TypeScript interfaces."""
        entities = ts_parser.parse(str(temp_ts_repo))
        model_entities = [e for e in entities if e.entity_type == EntityType.MODEL]
        assert len(model_entities) >= 1
        names = [e.name for e in model_entities]
        assert "CouponDto" in names

    def test_parse_sets_language_typescript(
        self, ts_parser: TypeScriptParser, temp_ts_repo: Path
    ) -> None:
        """All parsed entities should have language=TYPESCRIPT."""
        entities = ts_parser.parse(str(temp_ts_repo))
        for entity in entities:
            assert entity.language == Language.TYPESCRIPT

    def test_parse_excludes_spec_files(
        self, ts_parser: TypeScriptParser, temp_ts_repo: Path
    ) -> None:
        """parse() should exclude .spec.ts test files."""
        entities = ts_parser.parse(str(temp_ts_repo))
        for entity in entities:
            assert not entity.file_path.endswith(".spec.ts"), (
                f"Spec file should be excluded: {entity.file_path}"
            )

    def test_parse_excludes_declaration_files(
        self, ts_parser: TypeScriptParser, temp_ts_repo: Path
    ) -> None:
        """parse() should exclude .d.ts declaration files."""
        entities = ts_parser.parse(str(temp_ts_repo))
        for entity in entities:
            assert not entity.file_path.endswith(".d.ts"), (
                f"Declaration file should be excluded: {entity.file_path}"
            )

    def test_parse_empty_directory(
        self, ts_parser: TypeScriptParser, tmp_path: Path
    ) -> None:
        """parse() should return an empty list for a directory with no TS files."""
        result = ts_parser.parse(str(tmp_path))
        assert result == []


class TestTypeScriptParserExtractModels:
    """Tests for extract_models()."""

    def test_extract_models_returns_list(
        self, ts_parser: TypeScriptParser, temp_ts_repo: Path
    ) -> None:
        ts_parser.parse(str(temp_ts_repo))
        result = ts_parser.extract_models()
        assert isinstance(result, list)

    def test_extract_models_detects_interfaces(
        self, ts_parser: TypeScriptParser, temp_ts_repo: Path
    ) -> None:
        """extract_models() should return ModelNode objects for interfaces."""
        ts_parser.parse(str(temp_ts_repo))
        models = ts_parser.extract_models()
        assert any(m.entity_type == EntityType.MODEL for m in models)


class TestTypeScriptParserIsTestOrDeclarationFile:
    """Tests for the _is_test_or_declaration_file() helper."""

    def test_detects_spec_file(self, ts_parser: TypeScriptParser) -> None:
        assert ts_parser._is_test_or_declaration_file(
            Path("coupon-api.service.spec.ts")
        ) is True

    def test_detects_d_ts_file(self, ts_parser: TypeScriptParser) -> None:
        assert ts_parser._is_test_or_declaration_file(Path("coupon.d.ts")) is True

    def test_normal_ts_file(self, ts_parser: TypeScriptParser) -> None:
        assert ts_parser._is_test_or_declaration_file(
            Path("coupon-api.service.ts")
        ) is False
