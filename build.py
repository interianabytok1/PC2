"""Build a single-file local web application executable with PyInstaller."""

from PyInstaller.__main__ import run


if __name__ == "__main__":
    run([
        "app.py",
        "--name=PolozkyPreOberon",
        "--windowed",
        "--onefile",
        "--clean",
        "--noconfirm",
        "--distpath=release",
        "--workpath=build",
        "--specpath=build",
    ])