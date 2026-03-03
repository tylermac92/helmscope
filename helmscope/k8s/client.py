"""Kubernetes API client factory."""

from __future__ import annotations

from kubernetes import client  # type: ignore[import-untyped]
from kubernetes import config as k8s_config
from kubernetes.client import ApiClient  # type: ignore[import-untyped]

from helmscope.config import Config


class KubernetesConnectionError(Exception):
    """Raised when the Kubernetes cluster cannot be reached."""


def make_client(cfg: Config) -> ApiClient:
    """Construct an authenticated Kubernetes ApiClient from a Config.

    Raises KubernetesConnectionError if the cluster is unreachable.
    """
    try:
        k8s_config.load_kube_config(
            config_file=str(cfg.kubeconfig_path),
            context=cfg.context,
        )
    except Exception as exc:
        raise KubernetesConnectionError(
            f"Failed to connect to Kubernetes cluster: {exc}"
        ) from exc
    return ApiClient()


def make_core_v1_api(api_client: ApiClient) -> client.CoreV1Api:
    """Return a CoreV1Api instance from a shared ApiClient."""
    return client.CoreV1Api(api_client=api_client)


def make_apps_v1_api(api_client: ApiClient) -> client.AppsV1Api:
    """Return an AppsV1Api instance from a shared ApiClient."""
    return client.AppsV1Api(api_client=api_client)


def make_policy_v1_api(api_client: ApiClient) -> client.PolicyV1Api:
    """Return a PolicyV1Api instance from a shared ApiClient."""
    return client.PolicyV1Api(api_client=api_client)


def get_cluster_version(api_client: ApiClient) -> str:
    """Return the cluster version as a semver string e.g. '1.28.0'.

    Raises KubernetesConnectionError if the version endpoint is unreachable.
    """
    try:
        version_api = client.VersionApi(api_client=api_client)
        info = version_api.get_code()
        major = info.major.rstrip("+")
        minor = info.minor.rstrip("+")
        return f"{major}.{minor}.0"
    except Exception as exc:
        raise KubernetesConnectionError(
            f"Failed to retrieve cluster version: {exc}"
        ) from exc
