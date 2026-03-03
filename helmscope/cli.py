"""helmscope CLI entry point."""

from __future__ import annotations

import importlib.metadata
from pathlib import Path

import click

from helmscope.config import Config


def _get_version() -> str:
    """Read the package version from installed metadata."""
    return importlib.metadata.version("helmscope")


@click.group()
@click.version_option(version=_get_version(), prog_name="helmscope")
@click.option(
    "--context",
    default=None,
    help="Kubernetes context to use for cluster access.",
)
@click.option(
    "--namespace",
    "-n",
    default="default",
    show_default=True,
    help="Target namespace",
)
@click.option(
    "--all-namespaces",
    "-A",
    is_flag=True,
    default=False,
    help="Scan all namespaces; overrides --namespace.",
)
@click.option(
    "--kubeconfig",
    default=None,
    type=click.Path(path_type=Path),
    help="Path to kubeconfig file.",
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(
        ["terminal", "markdown", "html", "all"],
        case_sensitive=False,
    ),
    default="terminal",
    show_default=True,
    help="Output format.",
)
@click.option(
    "--output-dir",
    default="./helmscope-reports/",
    show_default=True,
    type=click.Path(path_type=Path),
    help="Directory for exported report files.",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    default=False,
    help="Suppress terminal output.",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Include passing checks in terminal output.",
)
@click.pass_context
def main(
    ctx: click.Context,
    context: str | None,
    namespace: str,
    all_namespaces: bool,
    kubeconfig: Path | None,
    output: str,
    output_dir: Path,
    quiet: bool,
    verbose: bool,
) -> None:
    """helmscope - Helm Release Auditor.
    Audits Helm releases running in a Kubernetes cluster and reports
    on their configuration and operational state.
    """
    ctx.ensure_object(dict)

    from helmscope.config import _default_kubeconfig_path

    resolved_kubeconfig = (
        kubeconfig if kubeconfig is not None else _default_kubeconfig_path()
    )

    cfg = Config(
        kubeconfig_path=resolved_kubeconfig,
        context=context,
        namespace=namespace,
        all_namespaces=all_namespaces,
    )

    ctx.obj["config"] = cfg
    ctx.obj["output"] = output
    ctx.obj["output_dir"] = output_dir
    ctx.obj["quiet"] = quiet
    ctx.obj["verbose"] = verbose


if __name__ == "__main__":
    main()
