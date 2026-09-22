import argparse
import asyncio
from datetime import UTC, datetime, timedelta

from scripts.common import operational_uow


async def main():
    parser = argparse.ArgumentParser(
        description="Remove sessions after 24-hour retention"
    )
    parser.add_argument("--batch-size", type=int, default=1000)
    args = parser.parse_args()
    if not 1 <= args.batch_size <= 10000:
        parser.error("Batch size must be between 1 and 10000")
    cutoff = datetime.now(UTC) - timedelta(hours=24)
    deleted = 0
    while True:
        async with operational_uow() as uow:
            count = await uow.sessions.cleanup(cutoff, args.batch_size)
            await uow.commit()
        deleted += count
        if count < args.batch_size:
            break
    print(f"Deleted {deleted} expired or revoked sessions")


if __name__ == "__main__":
    asyncio.run(main())
