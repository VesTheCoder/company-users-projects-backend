import argparse
import asyncio
from uuid import UUID

from app.auth.accounts import set_account_status
from scripts.common import operational_uow


async def main():
    parser = argparse.ArgumentParser(description="Activate or deactivate an account")
    parser.add_argument("--user-id", type=UUID, required=True)
    parser.add_argument("--status", choices=["activate", "deactivate"], required=True)
    args = parser.parse_args()
    async with operational_uow() as uow:
        await set_account_status(uow, args.user_id, args.status == "activate")


if __name__ == "__main__":
    asyncio.run(main())
