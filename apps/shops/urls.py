from django.urls import path

from .views import AreaDetailView, AreaListCreateView, ShareLinkCreateView, ShopDetailView, ShopListCreateView

urlpatterns = [
    path("areas/", AreaListCreateView.as_view(), name="area-list"),
    path("areas/<int:pk>/", AreaDetailView.as_view(), name="area-detail"),
    path("shops/", ShopListCreateView.as_view(), name="shop-list"),
    path("shops/<uuid:shop_alias>/", ShopDetailView.as_view(), name="shop-detail"),
    path("shops/<uuid:shop_alias>/share-links/", ShareLinkCreateView.as_view(), name="shop-share"),
]
