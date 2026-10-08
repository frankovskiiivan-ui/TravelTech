
import os
import sys
from pathlib import Path
from datetime import datetime

# ── Настройки ──────────────────────────────────────────────
SOURCE_DIR = input("Введите путь к папке проекта: ").strip().strip('"')
OUTPUT_FILE = input("Введите имя выходного файла (по умолчанию all_code.txt): ").strip()
if not OUTPUT_FILE:
    OUTPUT_FILE = "all_code.txt"

# Расширения файлов, которые считаем исходным кодом
CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".html", ".css", ".json", ".yaml", ".yml",
    ".sql", ".sh", ".bat", ".ps1", ".xml", ".toml", ".ini", ".cfg",
    ".dockerfile", ".gitignore", ".env.example", ".txt", ".md",
}

# Папки и файлы, которые исключаем
EXCLUDE_DIRS = {
    "__pycache__", ".git", ".idea", ".vscode", "venv", ".venv",
    "env", "node_modules", ".pytest_cache", ".mypy_cache",
    "build", "dist", ".eggs", ".sass-cache", ".next",
    "htmlcov", ".tox", "coverage", ".coverage",
}

EXCLUDE_FILES = {
    ".env", ".env.local", ".env.production",
}

EXCLUDE_PATTERNS = {
    ".pyc", ".pyo", ".pyd", ".so", ".dll", ".exe",
    ".db", ".sqlite3", ".log",
}

# Имена без расширения, которые тоже включаем
EXTRA_INCLUDE_NAMES = {
    "Dockerfile", "Makefile", "Procfile", ".dockerignore",
    "requirements.txt", ".env.example",
}

# ── Логика ─────────────────────────────────────────────────

def should_exclude(path: Path) -> bool:
    """Проверяет, нужно ли исключить файл или директорию."""
    parts = path.parts
    for part in parts:
        if part in EXCLUDE_DIRS:
            return True

    name = path.name
    if name in EXCLUDE_FILES:
        return True

    for pattern in EXCLUDE_PATTERNS:
        if name.endswith(pattern):
            return True

    return False


def is_code_file(path: Path) -> bool:
    """Проверяет, является ли файл исходным кодом."""
    if path.name in EXTRA_INCLUDE_NAMES:
        return True
    ext = path.suffix.lower()
    return ext in CODE_EXTENSIONS


def collect_files(root: Path) -> list:
    """Собирает все файлы кода, исключая мусор."""
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Фильтруем директории на лету (чтобы не заходить внутрь)
        dirnames[:] = [
            d for d in dirnames
            if d not in EXCLUDE_DIRS
        ]

        for fname in sorted(filenames):
            full = Path(dirpath) / fname
            rel = full.relative_to(root)

            if should_exclude(full):
                continue
            if not is_code_file(full):
                continue

            files.append(rel)
    return sorted(files)


def main():
    root = Path(SOURCE_DIR).resolve()
    if not root.exists():
        print(f"Папка не найдена: {root}")
        sys.exit(1)

    files = collect_files(root)

    if not files:
        print("Файлы кода не найдены.")
        sys.exit(0)

    output_path = Path(OUTPUT_FILE).resolve()

    with open(output_path, "w", encoding="utf-8") as out:
        out.write("=" * 70 + "\n")
        out.write(f" Сборка исходного кода проекта\n")
        out.write(f" Папка: {root}\n")
        out.write(f" Дата:  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        out.write(f" Файлов: {len(files)}\n")
        out.write("=" * 70 + "\n\n")

        out.write(" СОДЕРЖАНИЕ ФАЙЛОВ\n")
        out.write("-" * 70 + "\n\n")

        for i, rel in enumerate(files, 1):
            full = root / rel
            try:
                content = full.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                try:
                    content = full.read_text(encoding="cp1251")
                except Exception:
                    content = "[НЕ УДАЛОСЬ ПРОЧИТАТЬ ФАЙЛ — возможно, бинарный]"

            out.write(f"{'=' * 70}\n")
            out.write(f" ФАЙЛ {i}/{len(files)}: {rel}\n")
            out.write(f"{'=' * 70}\n")
            out.write(content)
            if not content.endswith("\n"):
                out.write("\n")
            out.write("\n")

        out.write("=" * 70 + "\n")
        out.write(f" КОНЕЦ СБОРКИ — всего файлов: {len(files)}\n")
        out.write("=" * 70 + "\n")

    print(f"\nГотово! Собрано файлов: {len(files)}")
    print(f"Результат: {output_path}")

    # Выводим список файлов
    print("\nСобранные файлы:")
    for f in files:
        print(f"  {f}")


if __name__ == "__main__":
    main()
