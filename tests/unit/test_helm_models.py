"""Unit tests for helmscope/helm/models.py."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from helmscope.helm.models import ChartMetadata, HelmRelease


def _make_chart_metadata(**overrides: object) -> ChartMetadata:
    defaults: dict[str, object] = {
        "name": "nginx-ingress",
        "version": "4.8.0",
        "app_version": "1.9.0",
        "api_version": "v2",
    }
    defaults.update(overrides)
    return ChartMetadata(**defaults)  # type: ignore[arg-type]


def _make_helm_release(**overrides: object) -> HelmRelease:
    defaults: dict[str, object] = {
        "name": "my-release",
        "namespace": "default",
        "chart": _make_chart_metadata(),
        "version": 1,
        "status": "deployed",
        "last_deployed": datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC),
        "values": {"replicaCount": 2},
        "manifest": "---\napiVersion: apps/v1\nkind: Deployment",
    }
    defaults.update(overrides)
    return HelmRelease(**defaults)  # type: ignore[arg-type]


class TestChartMetadata:
    def test_valid_construction(self) -> None:
        chart = _make_chart_metadata()
        assert chart.name == "nginx-ingress"
        assert chart.version == "4.8.0"
        assert chart.app_version == "1.9.0"
        assert chart.api_version == "v2"

    def test_app_version_is_optional(self) -> None:
        chart = _make_chart_metadata(app_version=None)
        assert chart.app_version is None

    def test_missing_required_field_raises(self) -> None:
        with pytest.raises(ValidationError):
            ChartMetadata(  # type: ignore[call-arg]
                version="4.8.0",
                api_version="v2",
            )

    def test_model_is_frozen(self) -> None:
        chart = _make_chart_metadata()
        with pytest.raises(ValidationError):
            chart.name = "other"  # type: ignore[misc]


class TestHelmRelease:
    def test_valid_construction(self) -> None:
        release = _make_helm_release()
        assert release.name == "my-release"
        assert release.namespace == "default"
        assert release.status == "deployed"
        assert release.version == 1

    def test_last_deployed_is_datetime(self) -> None:
        release = _make_helm_release()
        assert isinstance(release.last_deployed, datetime)
        assert release.last_deployed.tzinfo == UTC

    def test_parses_last_deployed_from_iso_string(self) -> None:
        release = _make_helm_release(last_deployed="2024-01-15T12:00:00+00:00")
        assert isinstance(release.last_deployed, datetime)
        assert release.last_deployed.tzinfo is not None

    def test_values_accepts_nested_dict(self) -> None:
        release = _make_helm_release(
            values={"image": {"tag": "1.25.0", "pullPolicy": "Always"}}
        )
        assert release.values["image"] == {
            "tag": "1.25.0",
            "pullPolicy": "Always",
        }

    def test_missing_required_field_raises(self) -> None:
        with pytest.raises(ValidationError):
            HelmRelease(  # type: ignore[call-arg]
                name="my-release",
                namespace="default",
            )

    def test_model_is_frozen(self) -> None:
        release = _make_helm_release()
        with pytest.raises(ValidationError):
            release.name = "other"  # type: ignore[misc]

    def test_chart_metadata_nested_correctly(self) -> None:
        release = _make_helm_release()
        assert isinstance(release.chart, ChartMetadata)
        assert release.chart.name == "nginx-ingress"
