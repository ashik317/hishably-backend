from django.urls import path

from .views import EntryListCreateView, ReverseEntryView, ShopLedgerView

urlpatterns = [
    path("entries/", EntryListCreateView.as_view(), name="entry-list"),
    path("entries/<int:pk>/reverse/", ReverseEntryView.as_view(), name="entry-reverse"),
    path("shops/<uuid:shop_alias>/ledger/", ShopLedgerView.as_view(), name="shop-ledger"),
]
