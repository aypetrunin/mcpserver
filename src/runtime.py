# src/runtime.py
import os
from pathlib import Path
from dotenv import load_dotenv


def init_runtime() -> None:
    """
    Загружает env-файл, если мы НЕ в Docker.

    Используется ВСЕМИ entrypoint'ами:
    - main_v2.py
    - cli / demo
    - фоновые джобы
    """
    is_docker = os.getenv("IS_DOCKER") == "1"
    if is_docker:
        return

    env = os.getenv("ENV", "dev").strip().lower()
    base_dir = Path(__file__).resolve().parents[1]  # /home/copilot_superuser/petrunin/zena/

    if env in ("prod", "production"):
        env_path = (base_dir / "../deploy/prod.env").resolve()
    else:
        env_path = (base_dir / "../deploy/dev.env").resolve()

    if not env_path.exists():
        raise RuntimeError(f"Env file not found: {env_path}")

    load_dotenv(env_path, override=False)
