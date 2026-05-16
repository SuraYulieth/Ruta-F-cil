import os
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
TEMP_DEPS = Path.home() / 'AppData' / 'Local' / 'Temp' / 'ruta-facil-python-deps'
LOCAL_VENDOR = BASE_DIR / 'vendor'

for path in (TEMP_DEPS, LOCAL_VENDOR, BASE_DIR):
    if path.exists():
        sys.path.insert(0, str(path))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

from django.core.management import execute_from_command_line


if __name__ == '__main__':
    execute_from_command_line([sys.argv[0], *sys.argv[1:]])
