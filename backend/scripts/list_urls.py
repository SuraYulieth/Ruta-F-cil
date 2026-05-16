from pathlib import Path
import os
import sys
import django
from django.urls import get_resolver


def find_backend_dir(start: Path) -> Path:
    current = start.resolve()

    for parent in [current, *current.parents]:
        if (parent / "manage.py").exists() and (parent / "core" / "settings.py").exists():
            return parent

    raise RuntimeError(
        "No se encontró la carpeta backend. Ejecuta este script desde el proyecto o verifica que existan manage.py y core/settings.py."
    )


BACKEND_DIR = find_backend_dir(Path(__file__).resolve())

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

django.setup()


def walk(patterns, prefix=""):
    lines = []

    for pattern in patterns:
        route = getattr(pattern, "pattern", "")
        name = getattr(pattern, "name", None)
        callback = getattr(pattern, "lookup_str", None)

        lines.append(f"{prefix}{route} | {type(pattern).__name__} | name={name} | callback={callback}")

        if hasattr(pattern, "url_patterns"):
            lines.extend(walk(pattern.url_patterns, prefix + "  "))

    return lines


if __name__ == "__main__":
    resolver = get_resolver(None)

    print("URLs registradas en Django:")
    print("=" * 80)

    for line in walk(resolver.url_patterns):
        print(line)
