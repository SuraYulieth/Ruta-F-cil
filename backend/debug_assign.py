import traceback
import os
import sys
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()
from logistics.models import Pedido
from logistics.serializers import PedidoDetailResponseSerializer
p = Pedido.objects.get(id=9)
print('pedido', p.id, p.estado, p.repartidor)
try:
    print(PedidoDetailResponseSerializer(p).data)
except Exception:
    traceback.print_exc()
