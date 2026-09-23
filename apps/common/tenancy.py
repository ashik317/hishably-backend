"""Multi-tenancy: every business-owned endpoint lives under /b/<business_alias>/.

BusinessScopedMixin resolves the business from the URL, checks the user is an active
member, and exposes `self.business` and `self.membership`. Views must filter querysets
with `business=self.business`, so one business can never see another's data.
"""
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import BasePermission

from apps.businesses.models import Business, Membership, Role


class BusinessScopedMixin:
    business = None  # set in initial(); None only while generating the API schema
    membership = None
    allowed_roles = None  # e.g. {Role.OWNER, Role.MANAGER}; None = any member
    write_roles = None  # roles allowed for unsafe methods; None = same as allowed_roles

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.business = get_object_or_404(Business, alias=kwargs["business_alias"])
        self.membership = (
            Membership.objects.filter(business=self.business, user=request.user, is_active=True)
            .select_related("user")
            .first()
        )
        if self.membership is None:
            # 404 instead of 403 so outsiders can't probe which businesses exist
            raise NotFound("Business not found.")
        roles = self.allowed_roles
        if request.method not in ("GET", "HEAD", "OPTIONS") and self.write_roles is not None:
            roles = self.write_roles
        if roles is not None and self.membership.role not in roles:
            raise PermissionDenied("Your role cannot do this.")

    @property
    def is_rep(self):
        return bool(self.membership) and self.membership.role == Role.REP

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        if hasattr(self, "business"):
            ctx["business"] = self.business
            ctx["membership"] = self.membership
        return ctx


class IsOwnerOrManager(BasePermission):
    def has_permission(self, request, view):
        m = getattr(view, "membership", None)
        return bool(m and m.role in (Role.OWNER, Role.MANAGER))
