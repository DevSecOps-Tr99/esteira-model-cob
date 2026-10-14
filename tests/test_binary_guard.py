from pathlib import Path

from esteira_model_cob import binary_guard

_ROOT = Path(__file__).resolve().parents[1]
_FIXTURES = _ROOT / "tests" / "fixtures"


def test_flagged_bytes_cover_full_ebcdic_control_range_without_overlap():
    assert binary_guard.NON_ROUNDTRIPPABLE.isdisjoint(binary_guard.NON_PRINTABLE)
    assert binary_guard.FLAGGED_BYTES == frozenset(range(0x40))


def test_clean_ebcdic_fixture_has_no_flagged_bytes():
    result = binary_guard.scan_file(_FIXTURES / "copybook_ebcdic_limpo.bin")
    assert result.flagged_bytes == []
    assert not result.requires_binary_transfer
    assert binary_guard.to_finding(result) is None


def test_hex_declarado_fixture_is_flagged():
    result = binary_guard.scan_file(_FIXTURES / "copybook_ebcdic_hex_declarado.bin")
    assert result.requires_binary_transfer
    assert 0x01 in result.flagged_bytes
    assert 0x25 in result.flagged_bytes
    assert result.has_non_roundtrippable


def test_to_finding_produces_critical_blocking_finding():
    result = binary_guard.scan_file(_FIXTURES / "copybook_ebcdic_hex_declarado.bin")
    finding = binary_guard.to_finding(result)
    assert finding is not None
    assert finding.rule_id == "BIN001"
    assert finding.severity == "critical"
    assert "0x01" in finding.message
    assert "0x25" in finding.message


def test_evaluate_returns_empty_list_for_clean_component():
    assert binary_guard.evaluate(_FIXTURES / "copybook_ebcdic_limpo.bin") == []
