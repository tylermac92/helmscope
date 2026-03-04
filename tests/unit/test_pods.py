"""Unit tests for helmscope/k8s/pods.py."""

from __future__ import annotations

from unittest.mock import MagicMock

from helmscope.k8s.pods import list_pods


def _make_pod(phase: str) -> MagicMock:
    pod = MagicMock()
    pod.status.phase = phase
    return pod


class TestListPods:
    def test_returns_running_pods(self) -> None:
        mock_api = MagicMock()
        mock_api.list_namespaced_pod.return_value.items = [
            _make_pod("Running"),
        ]
        result = list_pods(mock_api, ["default"])
        assert len(result) == 1

    def test_returns_pending_pods(self) -> None:
        mock_api = MagicMock()
        mock_api.list_namespaced_pod.return_value.items = [
            _make_pod("Pending"),
        ]
        result = list_pods(mock_api, ["default"])
        assert len(result) == 1

    def test_excludes_succeeded_pods(self) -> None:
        mock_api = MagicMock()
        mock_api.list_namespaced_pod.return_value.items = [
            _make_pod("Succeeded"),
        ]
        result = list_pods(mock_api, ["default"])
        assert result == []

    def test_excludes_failed_pods(self) -> None:
        mock_api = MagicMock()
        mock_api.list_namespaced_pod.return_value.items = [
            _make_pod("Failed"),
        ]
        result = list_pods(mock_api, ["default"])
        assert result == []

    def test_skips_namespace_on_403(self) -> None:
        from kubernetes.client.exceptions import (  # type: ignore[import-untyped]
            ApiException,
        )

        mock_api = MagicMock()
        mock_api.list_namespaced_pod.side_effect = ApiException(status=403)
        result = list_pods(mock_api, ["restricted"])
        assert result == []

    def test_iterates_multiple_namespaces(self) -> None:
        mock_api = MagicMock()
        mock_api.list_namespaced_pod.return_value.items = [
            _make_pod("Running"),
        ]
        result = list_pods(mock_api, ["ns-a", "ns-b", "ns-c"])
        assert len(result) == 3
        assert mock_api.list_namespaced_pod.call_count == 3

    def test_uses_one_api_call_per_namespace(self) -> None:
        mock_api = MagicMock()
        mock_api.list_namespaced_pod.return_value.items = []
        list_pods(mock_api, ["ns-a", "ns-b"])
        assert mock_api.list_namespaced_pod.call_count == 2

    def test_verifies_correct_namespace_passed(self) -> None:
        mock_api = MagicMock()
        mock_api.list_namespaced_pod.return_value.items = []
        list_pods(mock_api, ["production"])
        mock_api.list_namespaced_pod.assert_called_once_with(namespace="production")

    def test_empty_namespace_list_returns_empty(self) -> None:
        mock_api = MagicMock()
        result = list_pods(mock_api, [])
        assert result == []
        mock_api.list_namespaced_pod.assert_not_called()

    def test_pod_with_none_status_excluded(self) -> None:
        mock_api = MagicMock()
        pod = MagicMock()
        pod.status = None
        mock_api.list_namespaced_pod.return_value.items = [pod]
        result = list_pods(mock_api, ["default"])
        assert result == []
