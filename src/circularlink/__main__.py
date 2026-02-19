"""Entry point — invoked via `circularlink` CLI command."""
from __future__ import annotations

import sys


def main() -> None:
    """Launch the CircuLink Terminal application."""
    # Guard: Python 3.11+ required for match-statements and TaskGroup
    if sys.version_info < (3, 11):
        print(
            "CircuLink requires Python 3.11 or later.\n"
            f"You are running Python {sys.version}."
        )
        sys.exit(1)

    from circularlink.app import CircuLinkApp

    app = CircuLinkApp()
    app.run()


if __name__ == "__main__":
    main()
