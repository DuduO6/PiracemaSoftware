from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("auth/", include("register.urls")),
    path("api/", include("home.urls")),
    path("api/caminhoes/", include("caminhoes.urls")),
    path("api/", include("motoristas.urls")),
    path("api/viagens/", include("viagens.urls")),
    path("api/despesas/", include("despesas.urls")),
    path('api/acertos/', include('acertos.urls')),


]
