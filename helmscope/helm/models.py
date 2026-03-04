"""Pydantic models for Helm release data."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ChartMetadata(BaseModel):
    """Metadata from the Chart.yaml of a deployed chart."""

    model_config = ConfigDict(frozen=True)

    name: str
    version: str
    app_version: str | None = None
    api_version: str


class HelmRelease(BaseModel):
    """Represents a single decoded Helm release revision."""

    model_config = ConfigDict(frozen=True)

    name: str
    namespace: str
    chart: ChartMetadata
    version: int
    status: str
    last_deployed: datetime
    values: dict[str, object]
    manifest: str
