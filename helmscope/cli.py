"""helmscope CLI entry point."""
import click

@click.group()
def main() -> None:
    """helmscope - Helm Release Auditor."""

if __name__ == "__main__":
    main()
