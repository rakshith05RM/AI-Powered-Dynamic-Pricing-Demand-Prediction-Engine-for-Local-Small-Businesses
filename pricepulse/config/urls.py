from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from businesses import views as biz_views

urlpatterns = [
    path("admin/", admin.site.urls),

    # Public site + auth
    path("", biz_views.landing, name="landing"),
    path("register/", biz_views.register, name="accounts_register"),
    path("login/", biz_views.login_view, name="accounts_login"),
    path("logout/", biz_views.logout_view, name="accounts_logout"),
    path("onboarding/", biz_views.create_business, name="business_create"),

    # Dashboard pages (server-rendered)
    path("dashboard/", include("businesses.dashboard_urls")),

    # JSON APIs
    path("api/", include("products.urls")),
    path("api/", include("sales.urls")),
    path("api/", include("forecasting.urls")),
    path("api/", include("pricing.urls")),
    path("api/", include("inventory.urls")),
    path("api/", include("alerts.urls")),
    path("api/", include("analytics.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
