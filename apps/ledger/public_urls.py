from django.urls import path

from .views import PublicLedgerView

urlpatterns = [path("ledger/<str:token>/", PublicLedgerView.as_view(), name="public-ledger")]
