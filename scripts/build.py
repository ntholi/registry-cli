import PyInstaller.__main__


def main() -> None:
    PyInstaller.__main__.run(
        ["--onefile", "registry_cli/main.py", "--name", "registry"]
    )


if __name__ == "__main__":
    main()
