from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.businesses.urls")),
    path("api/v1/b/<uuid:business_alias>/", include("apps.shops.urls")),
    path("api/v1/b/<uuid:business_alias>/", include("apps.ledger.urls")),
    path("api/v1/b/<uuid:business_alias>/", include("apps.collections.urls")),
    path("api/v1/b/<uuid:business_alias>/", include("apps.notifications.urls")),
    path("api/v1/b/<uuid:business_alias>/", include("apps.reports.urls")),
    path("api/v1/public/", include("apps.ledger.public_urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]
