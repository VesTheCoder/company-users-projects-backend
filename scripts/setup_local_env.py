import secrets
from pathlib import Path


def main():
    target = Path(".env")
    if target.exists():
        raise SystemExit(".env already exists; keep or edit the existing configuration")
    content = Path(".env.sample").read_text()
    for placeholder in [
        "runtime-secret",
        "migration-secret",
        "bootstrap-secret",
        "at-least-32-random-bytes",
        "different-at-least-32-random-bytes",
    ]:
        content = content.replace(f"<{placeholder}>", secrets.token_urlsafe(32))
    target.write_text(content)
    print("Created development .env with random local credentials")


if __name__ == "__main__":
    main()
