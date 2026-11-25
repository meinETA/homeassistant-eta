"""The translation files must stay valid when branches are merged."""

import json
from pathlib import Path

import pytest

TRANSLATIONS = (
    Path(__file__).parents[3] / "custom_components" / "eta_webservices" / "translations"
)


def _no_duplicates(pairs: list[tuple[str, object]]) -> dict:
    keys = [key for key, _ in pairs]
    duplicates = sorted({key for key in keys if keys.count(key) > 1})
    assert not duplicates, f"duplicate keys: {duplicates}"
    return dict(pairs)


@pytest.mark.parametrize(
    "path", sorted(TRANSLATIONS.glob("*.json")), ids=lambda p: p.name
)
def test_no_duplicate_keys(path: Path) -> None:
    """Two branches adding the same block (e.g. "exceptions") merge without a conflict,
    but json keeps only the last one and the texts of the other branch are lost.
    """
    json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_no_duplicates)


def test_languages_have_the_same_keys() -> None:
    """Every text exists in every language."""

    def keys(node: object, prefix: str = "") -> set[str]:
        if not isinstance(node, dict):
            return {prefix}
        return set().union(*(keys(v, f"{prefix}/{k}") for k, v in node.items()))

    files = {
        p.name: keys(json.loads(p.read_text(encoding="utf-8")))
        for p in TRANSLATIONS.glob("*.json")
    }
    reference = files.pop("en.json")
    for name, found in files.items():
        assert found == reference, (
            f"{name}: missing {sorted(reference - found)}, extra {sorted(found - reference)}"
        )
