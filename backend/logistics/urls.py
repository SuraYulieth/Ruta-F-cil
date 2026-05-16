from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PedidoViewSet, RepartidorViewSet, AliadoViewSet, CustomUserViewSet, LoginView

router = DefaultRouter()
router.register(r'pedidos', PedidoViewSet)
router.register(r'repartidores', RepartidorViewSet)
router.register(r'aliados', AliadoViewSet)
router.register(r'users', CustomUserViewSet)

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('', include(router.urls)),
]
