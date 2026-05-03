"""Entry point for running the application."""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m app <command>")
        print()
        print("Commands:")
        print("  tui          Run the rich Text User Interface")
        print("  cli          Run the plain-text menu interface")
        print("  cmd <args>   Run the command-line interface (use --help for options)")
        print()
        print("Examples:")
        print("  python -m app tui")
        print("  python -m app cli")
        print("  python -m app cmd dashboard")
        print("  python -m app cmd members list")
        print("  python -m app cmd tx create --from 1 --to 2 --hours 2.0 'Garden help'")
        sys.exit(1)

    command = sys.argv[1]
    args = sys.argv[2:]

    if command == "tui":
        from app.tui.app import main as tui_main
        tui_main()
    elif command == "cli":
        from app.simple_cli import main as cli_main
        cli_main()
    elif command == "cmd":
        from app.cli import app
        sys.argv = [sys.argv[0]] + args
        app()
    else:
        print(f"Unknown command: {command}")
        print("Use 'tui', 'cli', or 'cmd'")
        sys.exit(1)


if __name__ == "__main__":
    main()
