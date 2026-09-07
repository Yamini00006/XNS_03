"""
backend/common/permissions.py

Small, hackathon-appropriate authorization helpers layered on top of
Django's built-in User model (is_staff / is_superuser). Every endpoint
already requires authentication by default (see REST_FRAMEWORK setting);
this adds the one extra rule the locked scope calls for: only the
uploader of a file (or a staff user) may delete it.
"""

from rest_framework.permissions import BasePermission


class IsOwnerOrStaff(BasePermission):
    """
    Object-level permission: allows access if request.user.is_staff,
    or if `obj_uploaded_by` (passed via has_object_permission) matches
    request.user.id.
    """

    message = "You do not have permission to modify this resource."

    def has_object_permission(self, request, view, obj_uploaded_by):
        user = request.user
        if user.is_staff or user.is_superuser:
            return True
        return obj_uploaded_by is not None and obj_uploaded_by == user.id