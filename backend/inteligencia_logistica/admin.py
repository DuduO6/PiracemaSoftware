from django.contrib import admin

from .models import (ConfiguracaoLogisticaEmpresa, DecisaoLogistica, Empresa,
                     CategoriaPolo, ClassificacaoPolo, FluxoLogistico, IndicadorFrete,
                     LocalLogistico, MembroEmpresa, ModeloLogisticoIA,
                     OportunidadeFrete, ParceiroFrete, PerfilEstrategia, PoloLogisticoNacional,
                     PracaPedagio, ProdutoLogistico, ResultadoAprendizadoLogistico, RotaEstrategica,
                     TarifaPedagio, TipoVeiculoPermitido)
from .models import RouteCache

admin.site.register((Empresa, MembroEmpresa, LocalLogistico, ParceiroFrete,
                     RotaEstrategica, PerfilEstrategia, ConfiguracaoLogisticaEmpresa,
                     OportunidadeFrete, DecisaoLogistica, ModeloLogisticoIA))
admin.site.register((PoloLogisticoNacional, CategoriaPolo, ClassificacaoPolo,
                     ProdutoLogistico, TipoVeiculoPermitido, IndicadorFrete,
                     FluxoLogistico, PracaPedagio, TarifaPedagio))
admin.site.register(RouteCache)
admin.site.register(ResultadoAprendizadoLogistico)
