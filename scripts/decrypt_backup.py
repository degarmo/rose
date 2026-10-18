"""Decrypt a nightly backup on your own computer. Never run this on the server.

    python scripts/decrypt_backup.py backup.dump.age --identity age-key.txt --output backup.dump

The identity file holds the age private key (the line starting
AGE-SECRET-KEY-). See docs/ops/restore.md. Requires `pip install pyrage`.
"""

import argparse
import sys
from pathlib import Path

import pyrage


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("backup", type=Path)
    parser.add_argument("--identity", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args()

    lines = options.identity.read_text().splitlines()
    secret = next((line.strip() for line in lines if line.startswith("AGE-SECRET-KEY-")), None)
    if secret is None:
        sys.exit("No AGE-SECRET-KEY- line in the identity file.")
    identity = pyrage.x25519.Identity.from_str(secret)
    with options.backup.open("rb") as sealed, options.output.open("wb") as plain:
        pyrage.decrypt_io(sealed, plain, [identity])
    print(f"Decrypted to {options.output}")


if __name__ == "__main__":
    main()
