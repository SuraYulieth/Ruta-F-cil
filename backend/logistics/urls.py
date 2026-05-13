from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PedidoViewSet, RepartidorViewSet, AliadoViewSet

router = DefaultRouter()
router.register(r'pedidos', PedidoViewSet)
router.register(r'repartidores', RepartidorViewSet)
router.register(r'aliados', AliadoViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
