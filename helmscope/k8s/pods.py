"""Kubernetes pod and container spec retrieval."""

from __future__ import annotations

import logging

from kubernetes.client import CoreV1Api, V1Pod  # type: ignore[import-untyped]
from kubernetes.client.exceptions import ApiException  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)


def list_pods(
    api: CoreV1Api,
    namespaces: list[str],
) -> list[V1Pod]:
    """Retrieve all running and pending pods across namespaces.

    Issues one API call per namespace, not one per pod.
    Skips namespaces where permission is denied.
    """
    pods: list[V1Pod] = []
    for namespace in namespaces:
        pods.extend(_list_pods_in_namespace(api, namespace))
    return pods


def _list_pods_in_namespace(
    api: CoreV1Api,
    namespace: str,
) -> list[V1Pod]:
    """Retrieve running and pending pods in a single namespace."""
    try:
        response = api.list_namespaced_pod(namespace=namespace)
    except ApiException as exc:
        if exc.status == 403:
            logger.warning(
                "Permission denied reading pods in namespace %r — skipping.",
                namespace,
            )
            return []
        raise

    return [pod for pod in response.items if _is_active_pod(pod)]


def _is_active_pod(pod: V1Pod) -> bool:
    """Return True if the pod is in Running or Pending phase."""
    phase: object = pod.status.phase if pod.status is not None else None
    return phase in ("Running", "Pending")
