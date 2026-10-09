"""Customer accounts manage karo (DATABASE_URL zaroori).

  python -m scripts.admin create <tenant-id> [--credits N]   naya customer + API key
  python -m scripts.admin add-credits <tenant-id> <N>        aur packs khareede
  python -m scripts.admin show <tenant-id>
  python -m scripts.admin deactivate|activate <tenant-id>
"""

import argparse
import asyncio
import os
import re
import sys

import asyncpg

from domain.accounts import generate_api_key, hash_api_key
from infrastructure.postgres_accounts import PostgresAccountRepository, UnknownTenant
from infrastructure.postgres_repository import create_pool


def _tenant(value: str) -> str:
    if not re.fullmatch(r"[a-z0-9-]{3,40}", value):
        raise argparse.ArgumentTypeError("lowercase letters, digits, dashes (3-40 chars)")
    return value


def _positive(value: str) -> int:
    n = int(value)
    if n < 1:
        raise argparse.ArgumentTypeError("must be >= 1")
    return n


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m scripts.admin")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("create")
    c.add_argument("tenant", type=_tenant)
    c.add_argument("--credits", type=_positive, default=1)
    a = sub.add_parser("add-credits")
    a.add_argument("tenant", type=_tenant)
    a.add_argument("amount", type=_positive)
    for name in ("show", "deactivate", "activate"):
        sub.add_parser(name).add_argument("tenant", type=_tenant)
    return p


async def _run(args: argparse.Namespace, dsn: str) -> str:
    pool = await create_pool(dsn)
    try:
        repo = PostgresAccountRepository(pool)
        if args.cmd == "create":
            key = generate_api_key()
            await repo.create(args.tenant, hash_api_key(key), args.credits)
            return (
                f"Created {args.tenant} with {args.credits} credit(s).\n"
                f"API key (customer ko bhejein — dobara nahi dikhegi): {key}"
            )
        if args.cmd == "add-credits":
            total = await repo.add_credits(args.tenant, args.amount)
            return f"{args.tenant}: +{args.amount} → {total} credit(s)"
        if args.cmd in ("activate", "deactivate"):
            await repo.set_active(args.tenant, args.cmd == "activate")
            return f"{args.tenant}: {args.cmd}d"
        return f"{args.tenant}: {await repo.get_credits(args.tenant)} credit(s)"
    finally:
        await pool.close()


def main() -> None:
    args = _parser().parse_args()
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        sys.exit("DATABASE_URL not set")
    try:
        sys.stdout.write(asyncio.run(_run(args, dsn)) + "\n")
    except UnknownTenant as exc:
        sys.exit(f"unknown tenant: {exc}")
    except asyncpg.UniqueViolationError:
        sys.exit(f"tenant {args.tenant!r} already exists")


if __name__ == "__main__":
    main()
