"""Загрузка .env из корня проекта. Импортируется до чтения os.getenv()."""
import os
from pathlib import Path


def load_env():
    """Читает .env из корня проекта (1 уровень вверх от shared/)."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        print(f"[env_loader] .env не найден: {env_path}")
        return False

    loaded = 0
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            os.environ.setdefault(k, v)
            loaded += 1
    
    print(f"[env_loader] Загружено переменных: {loaded}")
    return True


# Автозагрузка при импорте модуля
load_env()