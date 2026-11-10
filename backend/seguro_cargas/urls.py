from django.urls import path

from .views import CalcularSeguroCargasAPIView, ImportarDocumentoFiscalAPIView


urlpatterns = [
    path("calcular/", CalcularSeguroCargasAPIView.as_view(), name="seguro-cargas-calcular"),
    path("importar-xml/", ImportarDocumentoFiscalAPIView.as_view(), name="seguro-cargas-importar-xml"),
]
