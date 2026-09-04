from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAuthenticatedReadOnlyOrAdmin(BasePermission):
    """
    Authenticated users can perform safe/read-only requests.

    Only staff users can create, update, or delete resources.
    """

    def has_permission(
        self,
        request,
        view,
    ):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.method in SAFE_METHODS:
            return True

        return request.user.is_staff
