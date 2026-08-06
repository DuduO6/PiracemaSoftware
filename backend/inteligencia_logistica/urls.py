from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (CalculadoraFreteView, ConfiguracaoViewSet, DecisaoViewSet, IndicadorFreteViewSet, LocalLogisticoViewSet,
                    MinhasEmpresasView, ModeloIAViewSet, OportunidadeViewSet, ParceiroFreteViewSet,
                    PlanejamentoReposicionamentoView, PoloNacionalViewSet, ProdutoLogisticoViewSet, RegioesLogisticasView,
                    PerfilEstrategiaViewSet, RotaEstrategicaViewSet)

router = DefaultRouter()
router.register("locais", LocalLogisticoViewSet)
router.register("parceiros", ParceiroFreteViewSet)
router.register("rotas", RotaEstrategicaViewSet)
router.register("perfis", PerfilEstrategiaViewSet)
router.register("configuracoes", ConfiguracaoViewSet)
router.register("oportunidades", OportunidadeViewSet)
router.register("decisoes", DecisaoViewSet)
router.register("modelos", ModeloIAViewSet)
router.register("polos-nacionais", PoloNacionalViewSet)
router.register("produtos-logisticos", ProdutoLogisticoViewSet)
router.register("indicadores-frete", IndicadorFreteViewSet)

urlpatterns = [
    path("minhas-empresas/", MinhasEmpresasView.as_view(), name="minhas-empresas"),
    path("regioes-logisticas/", RegioesLogisticasView.as_view(), name="regioes-logisticas"),
    path("calcular-frete/", CalculadoraFreteView.as_view(), name="calcular-frete"),
    path("planejar-reposicionamento/", PlanejamentoReposicionamentoView.as_view(), name="planejar-reposicionamento"),
    path("", include(router.urls)),
]
