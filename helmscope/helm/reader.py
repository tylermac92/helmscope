"""Helm release reader — decodes Helm Secrets from the cluster."""

from __future__ import annotations

import base64
import gzip
import json
import logging
from datetime import UTC, datetime

import yaml
from kubernetes.client import CoreV1Api  # type: ignore[import-untyped]
from kubernetes.client.exceptions import ApiException  # type: ignore[import-untyped]
from pydantic import ValidationError

from helmscope.helm.models import ChartMetadata, HelmRelease

logger = logging.getLogger(__name__)

_HELM_LABEL_SELECTOR = "owner=helm,status=deployed"


def list_releases(
    api: CoreV1Api,
    namespaces: list[str],
) -> list[HelmRelease]:
    """Query and decode all deployed Helm releases across namespaces.

    Skips namespaces where permission is denied and malformed Secrets.
    """
    releases: list[HelmRelease] = []
    for namespace in namespaces:
        releases.extend(_list_releases_in_namespace(api, namespace))
    return releases


def _list_releases_in_namespace(
    api: CoreV1Api,
    namespace: str,
) -> list[HelmRelease]:
    """Decode all Helm release Secrets in a single namespace."""
    try:
        secrets = api.list_namespaced_secret(
            namespace=namespace,
            label_selector=_HELM_LABEL_SELECTOR,
        )
    except ApiException as exc:
        if exc.status == 403:
            logger.warning(
                "Permission denied reading Secrets in namespace %r — skipping.",
                namespace,
            )
            return []
        raise

    releases: list[HelmRelease] = []
    for secret in secrets.items:
        release = _decode_secret(secret, namespace)
        if release is not None:
            releases.append(release)
    return releases


def _decode_secret(
    secret: object,
    namespace: str,
) -> HelmRelease | None:
    """Decode a single Helm Secret into a HelmRelease model.

    Returns None and logs a warning if the Secret is malformed.
    """
    secret_name: str = getattr(getattr(secret, "metadata", None), "name", "<unknown>")
    try:
        raw_data: dict[str, str] = getattr(secret, "data", {}) or {}
        encoded = raw_data.get("release")
        if not encoded:
            logger.warning("Secret %r has no release field — skipping.", secret_name)
            return None
        return _decode_release_field(encoded, namespace)
    except Exception:
        logger.warning(
            "Failed to decode Secret %r — skipping.",
            secret_name,
            exc_info=True,
        )
        return None


def _decode_release_field(
    encoded: str,
    namespace: str,
) -> HelmRelease | None:
    """Run the full decode pipeline on a raw release field value."""
    try:
        helm_decoded = base64.b64decode(encoded)
        decompressed = gzip.decompress(helm_decoded)
        payload = json.loads(decompressed)
        return _parse_release(payload, namespace)
    except Exception:
        logger.warning(
            "Failed to decode release field — invalid base64, gzip, or JSON.",
            exc_info=True,
        )
        return None


def _parse_release(
    payload: dict[str, object],
    namespace: str,
) -> HelmRelease | None:
    """Build a HelmRelease from a decoded JSON payload."""
    try:
        info = payload.get("info")
        info = info if isinstance(info, dict) else {}

        chart = payload.get("chart")
        chart = chart if isinstance(chart, dict) else {}

        chart_meta = chart.get("metadata")
        chart_meta = chart_meta if isinstance(chart_meta, dict) else {}

        last_deployed = _parse_timestamp(info.get("last_deployed"))

        raw_version = payload.get("version")
        version = int(raw_version) if isinstance(raw_version, int) else 1

        raw_status = info.get("status")
        status = raw_status if isinstance(raw_status, str) else "unknown"

        raw_config = payload.get("config")
        values: dict[str, object] = raw_config if isinstance(raw_config, dict) else {}

        raw_manifest = payload.get("manifest")
        manifest = raw_manifest if isinstance(raw_manifest, str) else ""

        raw_name = payload.get("name")
        if not isinstance(raw_name, str):
            logger.warning("Release payload missing valid name field.")
            return None

        chart_name = chart_meta.get("name")
        chart_version = chart_meta.get("version")
        if not isinstance(chart_name, str) or not isinstance(chart_version, str):
            logger.warning("Chart metadata missing name or version.")
            return None

        raw_app_version = chart_meta.get("appVersion")
        app_version = raw_app_version if isinstance(raw_app_version, str) else None

        raw_api_version = chart_meta.get("apiVersion")
        api_version = raw_api_version if isinstance(raw_api_version, str) else "v2"

        return HelmRelease(
            name=raw_name,
            namespace=namespace,
            chart=ChartMetadata(
                name=chart_name,
                version=chart_version,
                app_version=app_version,
                api_version=api_version,
            ),
            version=version,
            status=status,
            last_deployed=last_deployed,
            values=values,
            manifest=manifest,
        )
    except (ValidationError, TypeError) as exc:
        logger.warning("Failed to parse release payload: %s", exc)
        return None


def _parse_timestamp(value: object) -> datetime:
    """Parse a Helm timestamp string into a timezone-aware UTC datetime."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value
    if isinstance(value, str):
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt
    return datetime.now(tz=UTC)


def parse_manifest(manifest_str: str) -> list[dict[str, object]]:
    """Split and parse a multi-document YAML manifest string.

    Returns a list of dicts, one per Kubernetes resource.
    Skips empty documents and resources missing apiVersion or kind.
    """
    resources: list[dict[str, object]] = []
    for doc in yaml.safe_load_all(manifest_str):
        if not doc:
            continue
        if not isinstance(doc, dict):
            continue
        if not doc.get("apiVersion") or not doc.get("kind"):
            logger.debug("Skipping resource missing apiVersion or kind: %r", doc)
            continue
        resources.append(doc)
    return resources
