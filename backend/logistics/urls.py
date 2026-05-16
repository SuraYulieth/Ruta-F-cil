from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PedidoViewSet, RepartidorViewSet, AliadoViewSet, CustomUserViewSet, LoginView, RutaViewSet

router = DefaultRouter()
router.register(r'pedidos', PedidoViewSet)
router.register(r'repartidores', RepartidorViewSet)
router.register(r'aliados', AliadoViewSet)
router.register(r'users', CustomUserViewSet)
router.register(r'routes', RutaViewSet, basename='routes')

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('', include(router.urls)),
]
