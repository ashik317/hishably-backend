from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied

from apps.common.tenancy import BusinessScopedMixin

from .models import Business, Membership, Role
from .serializers import BusinessSerializer, InviteSerializer, MemberSerializer


class BusinessListCreateView(generics.ListCreateAPIView):
    """Businesses I belong to; POST creates a new business with me as owner."""

    serializer_class = BusinessSerializer
    pagination_class = None

    def get_queryset(self):
        return (
            Business.objects.filter(memberships__user=self.request.user, memberships__is_active=True)
            .prefetch_related("memberships")
            .distinct()
        )


class BusinessDetailView(BusinessScopedMixin, generics.RetrieveUpdateAPIView):
    serializer_class = BusinessSerializer
    write_roles = {Role.OWNER, Role.MANAGER}

    def get_object(self):
        return self.business


class MemberListCreateView(BusinessScopedMixin, generics.ListCreateAPIView):
    allowed_roles = {Role.OWNER, Role.MANAGER}
    pagination_class = None

    def get_queryset(self):
        return Membership.objects.filter(business=self.business).select_related("user").order_by("created_at")

    def get_serializer_class(self):
        return InviteSerializer if self.request.method == "POST" else MemberSerializer

    def create(self, request, *args, **kwargs):
        s = InviteSerializer(data=request.data, context=self.get_serializer_context())
        s.is_valid(raise_exception=True)
        membership = s.save()
        return Response(MemberSerializer(membership).data, status=status.HTTP_201_CREATED)


class MemberDetailView(BusinessScopedMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = MemberSerializer
    allowed_roles = {Role.OWNER, Role.MANAGER}

    def get_queryset(self):
        return Membership.objects.filter(business=self.business).select_related("user")

    def perform_update(self, serializer):
        if serializer.instance.role == Role.OWNER:
            raise PermissionDenied("The owner's role can't be changed.")
        if serializer.validated_data.get("role") == Role.OWNER:
            raise PermissionDenied("Ownership transfer isn't supported here.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.role == Role.OWNER:
            raise PermissionDenied("The owner can't be removed.")
        instance.is_active = False  # keep history; entries still point to this person
        instance.save(update_fields=["is_active"])
