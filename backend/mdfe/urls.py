from django.urls import path

from .views import (
    FiscalConfigurationView,
    ManifestCloseView,
    MdfeCompaniesView,
    ManifestDetailView,
    ManifestHistoryView,
    ManifestListView,
    ManifestRefreshView,
    ManifestXmlDownloadView,
    ManifestXmlImportView,
    OperationConfirmView,
    OperationDetailView,
)


urlpatterns = [
    path("empresas/", MdfeCompaniesView.as_view(), name="mdfe-empresas"),
    path("pendentes/", ManifestListView.as_view(), name="mdfe-pendentes"),
    path("atualizar/", ManifestRefreshView.as_view(), name="mdfe-atualizar"),
    path("historico/", ManifestHistoryView.as_view(), name="mdfe-historico"),
    path("importar-xml/", ManifestXmlImportView.as_view(), name="mdfe-importar-xml"),
    path("configuracao/", FiscalConfigurationView.as_view(), name="mdfe-configuracao"),
    path("operacoes/<uuid:operation_id>/", OperationDetailView.as_view(), name="mdfe-operacao"),
    path("operacoes/<uuid:operation_id>/confirmar/", OperationConfirmView.as_view(), name="mdfe-operacao-confirmar"),
    path("<str:chave>/xml/", ManifestXmlDownloadView.as_view(), name="mdfe-download-xml"),
    path("<str:chave>/encerrar/", ManifestCloseView.as_view(), name="mdfe-encerrar"),
    path("<str:chave>/", ManifestDetailView.as_view(), name="mdfe-detalhe"),
]
