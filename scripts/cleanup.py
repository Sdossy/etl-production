"""
Resets local development data: deletes the SQLite database file(s)
and log files. Leaves data/sample/ untouched (that's committed source
data, not generated output).

Usage:
    python scripts/cleanup.py          # asks for confirmation
    python scripts/cleanup.py --yes    # skips confirmation
"""
import sys
from pathlib import Path

TARGETS = [
    Path("data/processed"),
    Path("logs"),
]


def main():
    skip_confirm = "--yes" in sys.argv

    files_to_remove = []
    for target in TARGETS:
        if target.exists():
            files_to_remove.extend(p for p in target.rglob("*") if p.is_file())

    if not files_to_remove:
        print("Nothing to clean up.")
        return

    print("Will delete:")
    for f in files_to_remove:
        print(f"  {f}")

    if not skip_confirm:
        confirm = input(f"\nDelete these {len(files_to_remove)} file(s)? [y/N] ")
        if confirm.lower() != "y":
            print("Cancelled.")
            return

    for f in files_to_remove:
        f.unlink()

    print(f"Deleted {len(files_to_remove)} file(s).")


if __name__ == "__main__":
    main()
