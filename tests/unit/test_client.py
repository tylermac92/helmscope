"""Unit tests for helmscope/k8s/client.py."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from helmscope.config import Config
from helmscope.k8s.client import (
    KubernetesConnectionError,
    get_cluster_version,
    make_client,
)


class TestMakeClient:
    def test_calls_load_kube_config_with_correct_args(self, tmp_path: Path) -> None:
        kubeconfig = tmp_path / "config"
        kubeconfig.write_text("placeholder")
        cfg = Config(
            kubeconfig_path=kubeconfig,
            context="my-context",
        )
        with patch("helmscope.k8s.client.k8s_config.load_kube_config") as mock_load:
            make_client(cfg)
            mock_load.assert_called_once_with(
                config_file=str(kubeconfig),
                context="my-context",
            )

    def test_raises_connection_error_on_failure(self, tmp_path: Path) -> None:
        cfg = Config(kubeconfig_path=tmp_path / "config")
        with (
            patch(
                "helmscope.k8s.client.k8s_config.load_kube_config",
                side_effect=Exception("unreachable"),
            ),
            pytest.raises(KubernetesConnectionError, match="unreachable"),
        ):
            make_client(cfg)

    def test_uses_none_context_when_not_specified(self, tmp_path: Path) -> None:
        kubeconfig = tmp_path / "config"
        kubeconfig.write_text("placeholder")
        cfg = Config(kubeconfig_path=kubeconfig)
        with patch("helmscope.k8s.client.k8s_config.load_kube_config") as mock_load:
            make_client(cfg)
            _, kwargs = mock_load.call_args
            assert kwargs["context"] is None


class TestGetClusterVersion:
    def test_returns_semver_string(self) -> None:
        mock_api_client = MagicMock()
        mock_version_info = MagicMock()
        mock_version_info.major = "1"
        mock_version_info.minor = "28"
        with patch("helmscope.k8s.client.client.VersionApi") as mock_version_api_cls:
            mock_version_api_cls.return_value.get_code.return_value = mock_version_info
            result = get_cluster_version(mock_api_client)
        assert result == "1.28.0"

    def test_strips_plus_suffix_from_version(self) -> None:
        mock_api_client = MagicMock()
        mock_version_info = MagicMock()
        mock_version_info.major = "1+"
        mock_version_info.minor = "29+"
        with patch("helmscope.k8s.client.client.VersionApi") as mock_version_api_cls:
            mock_version_api_cls.return_value.get_code.return_value = mock_version_info
            result = get_cluster_version(mock_api_client)
        assert result == "1.29.0"

    def test_raises_connection_error_on_failure(self) -> None:
        mock_api_client = MagicMock()
        with (
            patch(
                "helmscope.k8s.client.client.VersionApi",
                side_effect=Exception("connection refused"),
            ),
            pytest.raises(KubernetesConnectionError, match="connection refused"),
        ):
            get_cluster_version(mock_api_client)
