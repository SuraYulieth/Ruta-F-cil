from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PedidoViewSet, RepartidorViewSet, AliadoViewSet, CustomUserViewSet, 
    ImportExcelView, LoginView, RutaViewSet, DriverViewSet
)

router = DefaultRouter()
router.register(r'pedidos', PedidoViewSet)
router.register(r'repartidores', RepartidorViewSet)
router.register(r'aliados', AliadoViewSet)
router.register(r'users', CustomUserViewSet)
router.register(r'routes', RutaViewSet, basename='routes')
router.register(r'drivers', DriverViewSet, basename='drivers')

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('import-excel/', ImportExcelView.as_view(), name='import-excel'),
    path('', include(router.urls)),
]
