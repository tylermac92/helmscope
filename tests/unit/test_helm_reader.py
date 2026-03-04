"""Unit tests for helmscope/helm/reader.py."""

from __future__ import annotations

import base64
import gzip
import json
from datetime import UTC, datetime
from unittest.mock import MagicMock

from helmscope.helm.reader import (
    _decode_release_field,
    _parse_timestamp,
    list_releases,
    parse_manifest,
)


def _encode_payload(payload: dict[str, object]) -> str:
    """Encode a release payload the way Helm does."""
    json_bytes = json.dumps(payload).encode("utf-8")
    gzipped = gzip.compress(json_bytes)
    return base64.b64encode(gzipped).decode("utf-8")


VALID_PAYLOAD: dict[str, object] = {
    "name": "nginx-ingress",
    "version": 3,
    "info": {
        "status": "deployed",
        "last_deployed": "2024-01-15T12:00:00Z",
    },
    "chart": {
        "metadata": {
            "name": "ingress-nginx",
            "version": "4.8.0",
            "appVersion": "1.9.0",
            "apiVersion": "v2",
        }
    },
    "config": {"replicaCount": 2},
    "manifest": "---\napiVersion: apps/v1\nkind: Deployment\n",
}


class TestDecodeReleaseField:
    def test_round_trip_decode(self) -> None:
        encoded = _encode_payload(VALID_PAYLOAD)
        release = _decode_release_field(encoded, "ingress-nginx")
        assert release is not None
        assert release.name == "nginx-ingress"
        assert release.namespace == "ingress-nginx"
        assert release.status == "deployed"
        assert release.chart.name == "ingress-nginx"
        assert release.chart.version == "4.8.0"
        assert release.version == 3

    def test_invalid_base64_returns_none(self) -> None:
        result = _decode_release_field("!!!not-base64!!!", "default")
        assert result is None

    def test_invalid_gzip_returns_none(self) -> None:
        not_gzipped = base64.b64encode(b"plain text").decode("utf-8")
        result = _decode_release_field(not_gzipped, "default")
        assert result is None

    def test_missing_required_json_fields_returns_none(self) -> None:
        payload: dict[str, object] = {"version": 1}
        encoded = _encode_payload(payload)
        result = _decode_release_field(encoded, "default")
        assert result is None


class TestListReleases:
    def _make_mock_secret(self, name: str, encoded: str) -> MagicMock:
        secret = MagicMock()
        secret.metadata.name = name
        secret.data = {"release": encoded}
        return secret

    def test_returns_decoded_releases(self) -> None:
        encoded = _encode_payload(VALID_PAYLOAD)
        mock_secret = self._make_mock_secret("sh.helm.release.v1.nr.v3", encoded)
        mock_api = MagicMock()
        mock_api.list_namespaced_secret.return_value.items = [mock_secret]
        releases = list_releases(mock_api, ["ingress-nginx"])
        assert len(releases) == 1
        assert releases[0].name == "nginx-ingress"

    def test_skips_namespace_on_403(self) -> None:
        from kubernetes.client.exceptions import (  # type: ignore[import-untyped]
            ApiException,
        )

        mock_api = MagicMock()
        exc = ApiException(status=403)
        mock_api.list_namespaced_secret.side_effect = exc
        releases = list_releases(mock_api, ["restricted"])
        assert releases == []

    def test_skips_malformed_secret(self) -> None:
        mock_secret = self._make_mock_secret("bad-secret", "!!!bad!!!")
        mock_api = MagicMock()
        mock_api.list_namespaced_secret.return_value.items = [mock_secret]
        releases = list_releases(mock_api, ["default"])
        assert releases == []

    def test_scans_multiple_namespaces(self) -> None:
        encoded = _encode_payload(VALID_PAYLOAD)
        mock_secret = self._make_mock_secret("release-v1", encoded)
        mock_api = MagicMock()
        mock_api.list_namespaced_secret.return_value.items = [mock_secret]
        releases = list_releases(mock_api, ["namespace-a", "namespace-b"])
        assert len(releases) == 2
        assert mock_api.list_namespaced_secret.call_count == 2


class TestParseTimestamp:
    def test_parses_z_suffix(self) -> None:
        result = _parse_timestamp("2024-01-15T12:00:00Z")
        assert result.tzinfo == UTC
        assert result.year == 2024

    def test_parses_offset_string(self) -> None:
        result = _parse_timestamp("2024-01-15T12:00:00+00:00")
        assert result.tzinfo is not None

    def test_passthrough_aware_datetime(self) -> None:
        dt = datetime(2024, 1, 15, tzinfo=UTC)
        assert _parse_timestamp(dt) == dt

    def test_naive_datetime_gets_utc(self) -> None:
        dt = datetime(2024, 1, 15)
        result = _parse_timestamp(dt)
        assert result.tzinfo == UTC

    def test_unknown_type_returns_now(self) -> None:
        result = _parse_timestamp(None)
        assert result.tzinfo == UTC


class TestParseManifest:
    def test_parses_single_resource(self) -> None:
        manifest = (
            "apiVersion: apps/v1\n"
            "kind: Deployment\n"
            "metadata:\n"
            "  name: my-app\n"
            "  namespace: default\n"
        )
        result = parse_manifest(manifest)
        assert len(result) == 1
        assert result[0]["kind"] == "Deployment"

    def test_parses_multi_document_yaml(self) -> None:
        manifest = (
            "apiVersion: apps/v1\nkind: Deployment\n"
            "metadata:\n  name: app\n"
            "---\n"
            "apiVersion: v1\nkind: Service\n"
            "metadata:\n  name: svc\n"
        )
        result = parse_manifest(manifest)
        assert len(result) == 2

    def test_skips_empty_documents(self) -> None:
        manifest = "---\n---\napiVersion: v1\nkind: Service\n"
        result = parse_manifest(manifest)
        assert len(result) == 1

    def test_skips_resources_missing_api_version(self) -> None:
        manifest = "kind: Deployment\nmetadata:\n  name: app\n"
        result = parse_manifest(manifest)
        assert result == []

    def test_skips_resources_missing_kind(self) -> None:
        manifest = "apiVersion: apps/v1\nmetadata:\n  name: app\n"
        result = parse_manifest(manifest)
        assert result == []

    def test_empty_string_returns_empty_list(self) -> None:
        assert parse_manifest("") == []
