"""Helper script to generate encoded Helm Secret fixtures for tests."""

from __future__ import annotations

import base64
import gzip
import json

SAMPLE_RELEASE: dict[str, object] = {
    "name": "nginx-ingress",
    "namespace": "ingress-nginx",
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
    "manifest": (
        "---\napiVersion: apps/v1\nkind: Deployment\nmetadata:\n name: nginx-ingress\n"
    ),
}


def encode_release(payload: dict[str, object]) -> str:
    """Encode a release dict the same way Helm does."""
    json_bytes = json.dumps(payload).encode("utf-8")
    gzipped = gzip.compress(json_bytes)
    helm_encoded = base64.b64encode(gzipped).decode("utf-8")
    return helm_encoded


if __name__ == "__main__":
    encoded = encode_release(SAMPLE_RELEASE)
    print(encoded)
