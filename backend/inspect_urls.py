import sys, os
sys.path.insert(0, r'C:\Users\suray\AppData\Local\Temp\ruta-facil-python-deps')
sys.path.insert(0, r'C:\Users\suray\OneDrive\Escritorio\Ruta-F-cil\backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()
from django.urls import get_resolver
r = get_resolver(None)

def walk(patterns, prefix=''):
    lines = []
    for p in patterns:
        lines.append(f"{prefix}{p.pattern} {type(p).__name__} {getattr(p, 'lookup_str', None)}")
        if hasattr(p, 'url_patterns'):
            lines.extend(walk(p.url_patterns, prefix + '  '))
    return lines

for line in walk(r.url_patterns):
    print(line)
