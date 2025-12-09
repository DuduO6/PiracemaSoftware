from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("auth/", include("register.urls")),
    path("api/", include("home.urls")),
    path("api/caminhoes/", include("caminhoes.urls")),

]
