"""Build a portable desktop executable with PyInstaller."""

from PyInstaller.__main__ import run


if __name__ == "__main__":
    run([
        "app.py",
        "--name=PolozkyPreOberon",
        "--windowed",
        "--clean",
        "--noconfirm",
        "--distpath=release",
        "--workpath=build",
        "--specpath=build",
    ])