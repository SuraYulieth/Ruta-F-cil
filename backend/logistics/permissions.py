from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    """Permiso solo para administradores."""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'admin'


class IsDriver(permissions.BasePermission):
    """Permiso solo para repartidores."""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'driver'


class IsAlly(permissions.BasePermission):
    """Permiso solo para aliados."""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'aliado'


class IsAdminOrReadOnly(permissions.BasePermission):
    """Solo admin puede modificar, todos pueden leer."""
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return request.user and request.user.is_authenticated and request.user.role == 'admin'


class IsOwnerOrAdmin(permissions.BasePermission):
    """El usuario solo puede ver/modificar sus propios datos, admin ve todo."""
    def has_object_permission(self, request, view, obj):
        # Admin ve todo
        if request.user and request.user.role == 'admin':
            return True
        # El usuario solo ve sus propios datos
        if hasattr(obj, 'user') and obj.user == request.user:
            return True
        if hasattr(obj, 'repartidor') and obj.repartidor == request.user:
            return True
        if obj == request.user:
            return True
        return False


class IsDriverOwnerOrAdmin(permissions.BasePermission):
    """El repartidor solo ve/modifica sus propios pedidos, admin ve todo."""
    def has_object_permission(self, request, view, obj):
        # Admin ve todo
        if request.user and request.user.role == 'admin':
            return True
        # El repartidor solo ve sus propios pedidos
        if hasattr(obj, 'repartidor') and obj.repartidor == request.user:
            return True
        return False
