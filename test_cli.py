#!/usr/bin/env python3
import sys

sys.path.append(".")

from registry_cli.main import cli

if __name__ == "__main__":
    try:
        cli(["--help"])
    except SystemExit:
        pass  # Click calls sys.exit() after showing help

    print("CLI loaded successfully!")

    try:
        cli(["create", "--help"])
    except SystemExit:
        pass  # Click calls sys.exit() after showing help

    print("Create command group loaded successfully!")
