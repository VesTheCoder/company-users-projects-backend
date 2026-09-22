import argparse
import asyncio

from app.auth.accounts import create_user
from app.auth.passwords import PasswordHasherService
from app.auth.schemas import AccountCreate
from scripts.common import operational_uow, read_password


async def main():
    parser = argparse.ArgumentParser(description="Provision an application account")
    parser.add_argument("--login", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--password-stdin", action="store_true")
    args = parser.parse_args()
    data = AccountCreate(login=args.login, display_name=args.display_name)
    hashed = await PasswordHasherService().hash(read_password(args.password_stdin))
    async with operational_uow() as uow:
        print(await create_user(uow, data, hashed))


if __name__ == "__main__":
    asyncio.run(main())
