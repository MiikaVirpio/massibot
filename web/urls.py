from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("web/", include("chat.urls")),
    path("web/admin/", admin.site.urls),
]