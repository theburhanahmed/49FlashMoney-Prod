from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions allowed for any request,
        # so we'll always allow GET, HEAD, or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions only allowed to the owner of the object.
        # Assuming the object has a 'user' attribute that refers to the user
        if hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'owner'):
            return obj.owner == request.user
        return False


class IsAdminUser(permissions.BasePermission):
    """
    Custom permission to only allow admin users.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and (
            request.user.is_admin or request.user.is_staff or request.user.role == 'admin'
        )


class IsModeratorOrAdmin(permissions.BasePermission):
    """
    Custom permission to allow moderators and admins.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and (
            request.user.is_admin or 
            request.user.is_staff or 
            request.user.role in ['admin', 'moderator']
        )


class IsSameUserOrAdmin(permissions.BasePermission):
    """
    Custom permission to only allow users to access their own data or admins to access any user data.
    """
    def has_permission(self, request, view):
        # For detail views that need object-level permissions
        return True

    def has_object_permission(self, request, view, obj):
        # Allow admin users to access any object
        if (request.user.is_admin or request.user.is_staff or 
            request.user.role in ['admin', 'moderator']):
            return True
        
        # For User objects
        if hasattr(obj, 'id'):
            if hasattr(obj, 'pk'):  # This is likely a User instance
                return obj == request.user
            # If the object has a user attribute
            elif hasattr(obj, 'user'):
                return obj.user == request.user
            # If the object is being accessed via user pk in URL
            elif view.basename == 'user':
                user_id = view.kwargs.get('pk')
                if user_id:
                    return str(request.user.id) == user_id
        
        return False


class IsUserOrAdmin(permissions.BasePermission):
    """
    Custom permission to allow regular users and admins.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and (
            request.user.role in ['user', 'admin', 'moderator']
        )