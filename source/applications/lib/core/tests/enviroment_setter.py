# tests/test_test_config_provisioner_pytest.py
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

# ---- adjust these imports to your module layout ----
from core.config_loader import (
    ConfigAttribute,
    EnvConfigAttribute,
    FileConfigAttribute,
    NoKeyException,
    ConfigProvisioner,
)
# ----------------------------------------------------


@pytest.fixture
def mk_attrs() -> callable:
    def _mk_attrs(tmpdir: Path) -> list[ConfigAttribute[Any]]:
        return [
            EnvConfigAttribute[str](
                name="APP_NAME", default_value=None, value_type=str, is_secret=False
            ),
            EnvConfigAttribute[int](
                name="PORT", default_value=8080, value_type=int, is_secret=False
            ),
            EnvConfigAttribute[bool](
                name="DEBUG", default_value=False, value_type=bool, is_secret=False
            ),
            FileConfigAttribute[str](
                name="OAUTH_JSON",
                default_value=None,
                value_type=str,
                is_secret=True,
                file_location=str(tmpdir / "secrets" / "oauth.json"),
            ),
        ]

    return _mk_attrs


def test_sets_env_and_files_and_restores(
    tmp_path: Path, mk_attrs, monkeypatch: pytest.MonkeyPatch
):
    attrs = mk_attrs(tmp_path)
    oauth_payload = {"client_id": "abc", "client_secret": "xyz"}

    # pre-existing enviroment to verify restoration to previous value
    monkeypatch.setenv("PORT", "12345")

    with ConfigProvisioner(
        attributes=attrs,
        values={
            "APP_NAME": "e2e-runner",
            "DEBUG": True,  # ensure bool serializes
            "OAUTH_JSON": oauth_payload,  # dict -> JSON file
            # PORT omitted -> default 8080 appears in enviroment
        },
    ):
        # enviroment set
        assert os.environ.get("APP_NAME") == "e2e-runner"
        assert os.environ.get("PORT") == "8080"  # default as string
        assert os.environ.get("DEBUG") == "true"  # bool -> "true"

        # file created with JSON content
        path = tmp_path / "secrets" / "oauth.json"
        assert path.exists()
        content = json.loads(path.read_text(encoding="utf-8"))
        assert content == oauth_payload

    # after context → enviroment restored
    assert os.environ.get("PORT") == "12345"  # restored previous
    assert os.environ.get("APP_NAME") is None
    assert os.environ.get("DEBUG") is None

    # file removed because it did not exist before
    assert not (tmp_path / "secrets" / "oauth.json").exists()


def test_restores_existing_file_content(tmp_path: Path):
    existing = tmp_path / "secrets" / "oauth.json"
    existing.parent.mkdir(parents=True, exist_ok=True)
    existing.write_text('{"keep":"me"}', encoding="utf-8")

    attrs = [
        FileConfigAttribute[str](
            name="OAUTH_JSON",
            default_value=None,
            value_type=str,
            is_secret=True,
            file_location=str(existing),
        ),
    ]

    with ConfigProvisioner(
        attributes=attrs, values={"OAUTH_JSON": {"client_id": "new"}}
    ):
        # during context, file is overwritten
        data = json.loads(existing.read_text(encoding="utf-8"))
        assert data == {"client_id": "new"}

    # after context, original content is back
    data = json.loads(existing.read_text(encoding="utf-8"))
    assert data == {"keep": "me"}


def test_creates_missing_dirs(tmp_path: Path):
    deep_path = tmp_path / "a" / "b" / "c" / "config.txt"
    attrs = [
        FileConfigAttribute[str](
            name="DEEP_FILE",
            default_value=None,
            value_type=str,
            is_secret=False,
            file_location=str(deep_path),
        )
    ]
    with ConfigProvisioner(
        attributes=attrs,
        values={"DEEP_FILE": "hello"},
        create_missing_dirs=True,
    ):
        assert deep_path.exists()
        assert deep_path.read_text(encoding="utf-8") == "hello"

    # file was created in context and thus removed afterwards
    assert not deep_path.exists()


def test_raises_when_required_missing():
    attrs = [
        EnvConfigAttribute[str](
            name="MUST_HAVE",
            default_value=None,
            value_type=str,
            is_secret=False,
        ),
    ]
    with pytest.raises(NoKeyException):
        # nothing provided, no default → boom
        ConfigProvisioner(attributes=attrs, values={})


def test_bool_serialization_from_str():
    attrs = [
        EnvConfigAttribute[bool](
            name="FEATURE",
            default_value=False,
            value_type=bool,
            is_secret=False,
        ),
    ]

    # caller passes "True" string; provisioner should accept & pass through
    with ConfigProvisioner(attributes=attrs, values={"FEATURE": "True"}):
        assert os.environ.get("FEATURE") == "True"


def test_context_restores_on_exception(tmp_path: Path, mk_attrs):
    attrs = mk_attrs(tmp_path)
    raised = False
    try:
        with ConfigProvisioner(
            attributes=attrs,
            values={
                "APP_NAME": "x",
                "OAUTH_JSON": {"a": 1},
            },
        ):
            raise RuntimeError("boom")
    except RuntimeError:
        raised = True

    assert raised
    # enviroment restored even after exception
    assert os.environ.get("APP_NAME") is None
    # file removed
    assert not (tmp_path / "secrets" / "oauth.json").exists()


def test_accepts_list_of_pairs(tmp_path: Path, mk_attrs):
    attrs = mk_attrs(tmp_path)
    kv = [
        ("APP_NAME", "pairlist"),
        ("DEBUG", False),
        ("PORT", 9999),
        ("OAUTH_JSON", {"client_id": "t"}),
    ]
    with ConfigProvisioner(attributes=attrs, values=kv):
        assert os.environ.get("APP_NAME") == "pairlist"
        assert os.environ.get("PORT") == "9999"
        assert os.environ.get("DEBUG") == "false"
