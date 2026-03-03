"""Unit tests for helmscope/config.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from helmscope.config import DEFAULT_KUBECONFIG, Config, _default_kubeconfig_path


class TestDefaultKubeconfigPath:
    def test_returns_default_when_env_not_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("KUBECONFIG", raising=False)
        assert _default_kubeconfig_path() == DEFAULT_KUBECONFIG

    def test_returns_env_var_path_when_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("KUBECONFIG", "/custom/path/config")
        assert _default_kubeconfig_path() == Path("/custom/path/config")


class TestConfigValidate:
    def test_passes_when_kubeconfig_exists(self, tmp_path: Path) -> None:
        kubeconfig = tmp_path / "config"
        kubeconfig.write_text("placeholder")
        config = Config(kubeconfig_path=kubeconfig)
        config.validate()  # should not raise

    def test_exits_when_kubeconfig_missing(self, tmp_path: Path) -> None:
        config = Config(kubeconfig_path=tmp_path / "nonexistent")
        with pytest.raises(SystemExit) as exc_info:
            config.validate()
        assert "kubeconfig file not found" in str(exc_info.value)

    def test_explicit_kubeconfig_flag(self, tmp_path: Path) -> None:
        kubeconfig = tmp_path / "custom_config"
        kubeconfig.write_text("placeholder")
        config = Config(kubeconfig_path=kubeconfig)
        assert config.kubeconfig_path == kubeconfig
        config.validate()  # should not raise


class TestResolveNamespaces:
    def test_returns_single_namespace_when_all_namespaces_false(self) -> None:
        config = Config(namespace="production", all_namespaces=False)
        assert config.resolve_namespaces() == ["production"]

    def test_returns_all_namespaces_when_flag_set(self) -> None:
        config = Config(all_namespaces=True)
        result = config.resolve_namespaces(
            all_cluster_namespaces=["default", "production", "staging"]
        )
        assert result == ["default", "production", "staging"]

    def test_raises_when_all_namespaces_true_but_list_not_provided(self) -> None:
        config = Config(all_namespaces=True)
        with pytest.raises(ValueError, match="all_cluster_namespaces must be provided"):
            config.resolve_namespaces()
