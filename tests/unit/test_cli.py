"""Unit tests for helmscope/cli.py."""

from __future__ import annotations

from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from helmscope.cli import main
from helmscope.config import Config


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture()
def kubeconfig(tmp_path: Path) -> Path:
    kc = tmp_path / "config"
    kc.write_text("placeholder")
    return kc


class TestVersionFlag:
    def test_version_flag_prints_version(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "helmscope" in result.output


class TestGlobalFlags:
    def test_default_flags_produce_correct_config(
        self,
        runner: CliRunner,
        kubeconfig: Path,
    ) -> None:
        captured: dict[str, object] = {}

        @main.command("probe2")
        @click.pass_context
        def probe(ctx: click.Context) -> None:
            captured.update(ctx.obj)

        result = runner.invoke(
            main,
            [
                "--kubeconfig",
                str(kubeconfig),
                "--namespace",
                "staging",
                "probe2",
            ],
        )
        assert result.exit_code == 0
        cfg = captured["config"]
        assert isinstance(cfg, Config)
        assert cfg.namespace == "staging"
        assert cfg.all_namespaces is False

    def test_all_namespaces_flag(
        self,
        runner: CliRunner,
        kubeconfig: Path,
    ) -> None:
        captured: dict[str, object] = {}

        @main.command("probe3")
        @click.pass_context
        def probe(ctx: click.Context) -> None:
            captured.update(ctx.obj)

        result = runner.invoke(
            main,
            [
                "--kubeconfig",
                str(kubeconfig),
                "--all-namespaces",
                "probe3",
            ],
        )
        assert result.exit_code == 0
        cfg = captured["config"]
        assert isinstance(cfg, Config)
        assert cfg.all_namespaces is True

    def test_output_defaults_to_terminal(
        self,
        runner: CliRunner,
        kubeconfig: Path,
    ) -> None:
        captured: dict[str, object] = {}

        @main.command("probe4")
        @click.pass_context
        def probe(ctx: click.Context) -> None:
            captured.update(ctx.obj)

        result = runner.invoke(
            main,
            ["--kubeconfig", str(kubeconfig), "probe4"],
        )
        assert result.exit_code == 0
        assert captured["output"] == "terminal"

    def test_invalid_output_format_rejected(
        self,
        runner: CliRunner,
        kubeconfig: Path,
    ) -> None:
        result = runner.invoke(
            main,
            [
                "--kubeconfig",
                str(kubeconfig),
                "--output",
                "pdf",
            ],
        )
        assert result.exit_code != 0
        assert "Invalid value" in result.output

    def test_help_flag(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "--namespace" in result.output
        assert "--all-namespaces" in result.output
        assert "--output" in result.output
        assert "--quiet" in result.output
        assert "--verbose" in result.output
