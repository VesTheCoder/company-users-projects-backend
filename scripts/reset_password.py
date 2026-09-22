import argparse
import asyncio
from uuid import UUID

from app.auth.accounts import reset_password
from app.auth.passwords import PasswordHasherService
from scripts.common import operational_uow, read_password


async def main():
    parser = argparse.ArgumentParser(description="Reset password and revoke sessions")
    parser.add_argument("--user-id", type=UUID, required=True)
    parser.add_argument("--password-stdin", action="store_true")
    args = parser.parse_args()
    hashed = await PasswordHasherService().hash(read_password(args.password_stdin))
    async with operational_uow() as uow:
        await reset_password(uow, args.user_id, hashed)


if __name__ == "__main__":
    asyncio.run(main())
