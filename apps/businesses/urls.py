from django.urls import path

from .views import BusinessDetailView, BusinessListCreateView, MemberDetailView, MemberListCreateView

urlpatterns = [
    path("businesses/", BusinessListCreateView.as_view(), name="business-list"),
    path("b/<uuid:business_alias>/", BusinessDetailView.as_view(), name="business-detail"),
    path("b/<uuid:business_alias>/members/", MemberListCreateView.as_view(), name="member-list"),
    path("b/<uuid:business_alias>/members/<int:pk>/", MemberDetailView.as_view(), name="member-detail"),
]
