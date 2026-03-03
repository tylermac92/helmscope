"""CLI configuration and kubeconfig resolution."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_KUBECONFIG = Path.home() / ".kube" / "config"
DEFAULT_NAMESPACE = "default"


def _default_kubeconfig_path() -> Path:
    """Resolve kubeconfig path from KUBECONFIG env var or default location."""
    env_val = os.environ.get("KUBECONFIG")
    if env_val:
        return Path(env_val)
    return DEFAULT_KUBECONFIG


@dataclass
class Config:
    """Holds resolved CLI configuration for a helmscope invocation."""

    kubeconfig_path: Path = field(default_factory=_default_kubeconfig_path)
    context: str | None = None
    namespace: str = DEFAULT_NAMESPACE
    all_namespaces: bool = False

    def validate(self) -> None:
        """Raise SystemExit if the kubeconfig file cannot be found or read."""
        if not self.kubeconfig_path.exists():
            raise SystemExit(
                f"Error: kubeconfig file not found: {self.kubeconfig_path}\n"
                "Set up the KUBECONFIG environment variable or use --kubeconfig."
            )

    def resolve_namespaces(
        self, all_cluster_namespaces: list[str] | None = None
    ) -> list[str]:
        """Return the list of namespaces to scan.
        If all_namespaces is True, returns all_cluster_namespaces (which the
        caller must supply by querying the API). Otherwise returns [namespace].
        """
        if self.all_namespaces:
            if all_cluster_namespaces is None:
                raise ValueError(
                    "all_cluster_namespaces must be provided when all_namespaces=True"
                )
            return all_cluster_namespaces
        return [self.namespace]
