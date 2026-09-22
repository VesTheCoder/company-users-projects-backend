import json
from pathlib import Path

from app.main import create_app


def main():
    output = Path("docs/openapi.json")
    output.parent.mkdir(exist_ok=True)
    output.write_text(
        json.dumps(create_app().openapi(), indent=2) + "\n", encoding="utf-8"
    )
    print(output)


if __name__ == "__main__":
    main()
