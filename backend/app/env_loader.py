import os
from pathlib import Path


def parse_env_value(value: str) -> str:
    cleaned = value.strip()

    if (
        len(cleaned) >= 2
        and cleaned[0] == cleaned[-1]
        and cleaned[0] in {"'", '"'}
    ):
        return cleaned[1:-1]

    return cleaned


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for line in path.read_text().splitlines():
        stripped = line.strip()

        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue

        key, value = stripped.split("=", 1)
        key = key.strip()

        if key and key not in os.environ:
            os.environ[key] = parse_env_value(value)


def load_dotenv() -> None:
    app_dir = Path(__file__).resolve().parent
    backend_dir = app_dir.parent
    project_dir = backend_dir.parent

    for env_path in [project_dir / ".env", backend_dir / ".env"]:
        load_env_file(env_path)
