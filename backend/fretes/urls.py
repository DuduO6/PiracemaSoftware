from django.urls import path

from .views import CalcularFreteAPIView, MunicipiosAPIView


urlpatterns = [
    path("calcular/", CalcularFreteAPIView.as_view(), name="fretes-calcular"),
    path("municipios/", MunicipiosAPIView.as_view(), name="fretes-municipios"),
]
