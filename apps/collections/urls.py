from django.urls import path

from .views import ConfirmHandoverView, HandoverListCreateView, MyRouteView, VisitListCreateView

urlpatterns = [
    path("reps/me/route/", MyRouteView.as_view(), name="my-route"),
    path("visits/", VisitListCreateView.as_view(), name="visit-list"),
    path("handovers/", HandoverListCreateView.as_view(), name="handover-list"),
    path("handovers/<int:pk>/confirm/", ConfirmHandoverView.as_view(), name="handover-confirm"),
]
