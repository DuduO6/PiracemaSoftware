from django.urls import path

from .views import CalcularSeguroCargasAPIView


urlpatterns = [
    path("calcular/", CalcularSeguroCargasAPIView.as_view(), name="seguro-cargas-calcular"),
]
