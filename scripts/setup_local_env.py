from pathlib import Path


def main():
    target = Path(".env")
    if target.exists():
        raise SystemExit(".env already exists; keep or edit the existing configuration")
    target.write_text(Path(".env.sample").read_text())
    print("Created development .env from .env.sample")


if __name__ == "__main__":
    main()
