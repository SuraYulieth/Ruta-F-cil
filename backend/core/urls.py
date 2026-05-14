from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse


def home(request):
    return JsonResponse({
        'message': 'Ruta Facil backend activo',
        'api': '/api/',
        'admin': '/admin/'
    })

urlpatterns = [
    path('', home),
    path('admin/', admin.site.urls),
    path('api/', include('logistics.urls')),
]
