from decimal import Decimal
from math import sqrt

from django.utils import timezone

from .models import ModeloLogisticoIA, ResultadoAprendizadoLogistico


FEATURES = ("receita", "custo_estimado", "km_vazio", "distancia_carregada_km", "tempo_espera_horas",
            "probabilidade_continuidade", "risco_retorno_vazio")


def features_oportunidade(oportunidade):
    return {nome: float(getattr(oportunidade, nome) or 0) for nome in FEATURES}


def prever_lucro(modelo, features):
    metricas = modelo.metricas or {}
    medias, escalas, coeficientes = metricas.get("medias", {}), metricas.get("escalas", {}), metricas.get("coeficientes", {})
    previsao = float(metricas.get("intercepto", 0))
    for nome in FEATURES:
        escala = float(escalas.get(nome, 1)) or 1
        previsao += ((float(features.get(nome, 0)) - float(medias.get(nome, 0))) / escala) * float(coeficientes.get(nome, 0))
    return previsao


def treinar_modelo_lucro(empresa, minimo_registros=30, iteracoes=2500, taxa=0.02):
    registros = list(ResultadoAprendizadoLogistico.objects.filter(
        empresa=empresa, lucro_real__isnull=False
    ).order_by("id"))
    if len(registros) < minimo_registros:
        raise ValueError(f"São necessários {minimo_registros} resultados reais; existem {len(registros)}.")
    matriz_total = [[float(item.features.get(nome, 0)) for nome in FEATURES] for item in registros]
    alvos_total = [float(item.lucro_real) for item in registros]
    corte = max(1, int(len(registros) * 0.8))
    matriz, alvos = matriz_total[:corte], alvos_total[:corte]
    matriz_validacao, alvos_validacao = matriz_total[corte:], alvos_total[corte:]
    medias = {nome: sum(linha[i] for linha in matriz) / len(matriz) for i, nome in enumerate(FEATURES)}
    escalas = {}
    for i, nome in enumerate(FEATURES):
        variancia = sum((linha[i] - medias[nome]) ** 2 for linha in matriz) / len(matriz)
        escalas[nome] = sqrt(variancia) or 1.0
    x = [[(linha[i] - medias[nome]) / escalas[nome] for i, nome in enumerate(FEATURES)] for linha in matriz]
    pesos, intercepto = [0.0] * len(FEATURES), sum(alvos) / len(alvos)
    for _ in range(iteracoes):
        erros = [intercepto + sum(peso * valor for peso, valor in zip(pesos, linha)) - alvo for linha, alvo in zip(x, alvos)]
        intercepto -= taxa * sum(erros) / len(erros)
        for coluna in range(len(pesos)):
            pesos[coluna] -= taxa * sum(erro * linha[coluna] for erro, linha in zip(erros, x)) / len(erros)
    x_validacao = [[(linha[i] - medias[nome]) / escalas[nome] for i, nome in enumerate(FEATURES)] for linha in matriz_validacao]
    previsoes_validacao = [intercepto + sum(peso * valor for peso, valor in zip(pesos, linha)) for linha in x_validacao]
    mae = (sum(abs(previsto - real) for previsto, real in zip(previsoes_validacao, alvos_validacao)) / len(alvos_validacao)) if alvos_validacao else 0
    versao = timezone.now().strftime("lucro-%Y%m%d%H%M%S")
    ModeloLogisticoIA.objects.filter(empresa=empresa, tipo_modelo="REGRESSAO_LUCRO", status=ModeloLogisticoIA.Status.ATIVO).update(status=ModeloLogisticoIA.Status.SUBSTITUIDO)
    return ModeloLogisticoIA.objects.create(
        empresa=empresa, tipo_modelo="REGRESSAO_LUCRO", versao=versao, algoritmo="Regressão linear padronizada",
        quantidade_registros=len(registros), features_utilizadas=list(FEATURES), status=ModeloLogisticoIA.Status.ATIVO,
        data_treinamento=timezone.now(), metricas={"mae_validacao": round(mae, 2), "registros_treino": len(alvos),
            "registros_validacao": len(alvos_validacao), "intercepto": intercepto,
            "coeficientes": dict(zip(FEATURES, pesos)), "medias": medias, "escalas": escalas},
        observacoes="Modelo treinado somente com resultados operacionais reais registrados após decisões.",
    )
