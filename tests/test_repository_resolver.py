import importlib.util
import json
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).parents[1] / "server" / "repository_resolver.py"
SPEC = importlib.util.spec_from_file_location("repository_resolver", MODULE_PATH)
resolver = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(resolver)


def configure(monkeypatch, tmp_path, aliases):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"repositoriesRoot": str(tmp_path / "repos"), "aliases": aliases}))
    monkeypatch.setattr(resolver, "CONFIG_PATH", config_path)


def test_resolves_alias_to_verified_checkout(monkeypatch, tmp_path):
    configure(monkeypatch, tmp_path, {"web": "example-org/storefront"})
    checkout = tmp_path / "repos" / "example-org" / "storefront"
    checkout.mkdir(parents=True)
    monkeypatch.setattr(resolver, "origin_for", lambda path: "example-org/storefront")

    assert resolver.resolve_repository("@web") == {
        "status": "found",
        "repository": "example-org/storefront",
        "path": str(checkout),
    }


def test_lists_aliases_for_bare_owner(monkeypatch, tmp_path):
    configure(
        monkeypatch,
        tmp_path,
        {"web": "example-org/storefront", "api": "example-org/api-service", "other": "other-org/tool"},
    )

    assert resolver.resolve_repository("@example-org/") == {
        "status": "ambiguous",
        "owner": "example-org",
        "aliases": {"web": "example-org/storefront", "api": "example-org/api-service"},
    }


def test_reports_missing_checkout(monkeypatch, tmp_path):
    configure(monkeypatch, tmp_path, {"web": "example-org/storefront"})

    result = resolver.resolve_repository("@web")

    assert result["status"] == "missing"
    assert result["repository"] == "example-org/storefront"


def test_reports_origin_mismatch(monkeypatch, tmp_path):
    configure(monkeypatch, tmp_path, {"web": "example-org/storefront"})
    checkout = tmp_path / "repos" / "example-org" / "storefront"
    checkout.mkdir(parents=True)
    monkeypatch.setattr(resolver, "origin_for", lambda path: "example-org/different-project")

    assert resolver.resolve_repository("@web") == {
        "status": "mismatch",
        "repository": "example-org/storefront",
        "path": str(checkout),
        "origin": "example-org/different-project",
    }


def test_refuses_clone_without_confirmation(monkeypatch, tmp_path):
    configure(monkeypatch, tmp_path, {"web": "example-org/storefront"})

    with pytest.raises(ValueError, match="requires confirmed=true"):
        resolver.clone_repository("example-org/storefront", confirmed=False)
