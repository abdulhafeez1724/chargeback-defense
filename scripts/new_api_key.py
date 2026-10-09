"""Naye customer ke liye API key banao: python scripts/new_api_key.py <tenant_id>"""

import re
import secrets
import sys


def main() -> None:
    if len(sys.argv) != 2 or not re.fullmatch(r"[a-z0-9-]{3,40}", sys.argv[1]):
        sys.exit("usage: new_api_key.py <tenant-id>  (lowercase letters, digits, dashes)")
    tenant = sys.argv[1]
    key = "cbd_" + secrets.token_urlsafe(24)
    sys.stdout.write(
        f"API key (customer ko email karein): {key}\n"
        f"CHARGEBACK_API_KEYS me add karein:  {key}:{tenant}\n"
    )


if __name__ == "__main__":
    main()
