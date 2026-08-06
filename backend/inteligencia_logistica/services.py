from decimal import Decimal

from django.db.models import Count
from django.utils import timezone

from .ml import features_oportunidade, prever_lucro
from .models import (ConfiguracaoLogisticaEmpresa, ModeloLogisticoIA, OportunidadeFrete,
                     ResultadoAprendizadoLogistico)


PESOS_PADRAO = {
    "lucro": Decimal("0.45"),
    "km_vazio": Decimal("0.20"),
    "tempo_espera": Decimal("0.10"),
    "continuidade": Decimal("0.20"),
    "risco": Decimal("0.05"),
}
ORDEM_NIVEL = {"GLOBAL": 0, "OPERACAO": 1, "CAMINHAO": 2, "CARRETA": 3, "DECISAO": 4}


def resolver_configuracao(empresa, contexto=None):
    contexto = contexto or {}
    candidatas = ConfiguracaoLogisticaEmpresa.objects.filter(empresa=empresa, ativo=True)
    validas = []
    for config in candidatas:
        if config.nivel == "OPERACAO" and config.operacao != contexto.get("operacao"):
            continue
        if config.nivel == "CAMINHAO" and config.caminhao_id != contexto.get("caminhao_id"):
            continue
        if config.nivel == "CARRETA" and config.carreta_id != contexto.get("carreta_id"):
            continue
        if config.nivel == "DECISAO" and config.decisao_referencia != contexto.get("decisao_referencia"):
            continue
        validas.append(config)
    return max(validas, key=lambda item: ORDEM_NIVEL[item.nivel], default=None)


def _normalizar(valor, maximo):
    if maximo <= 0:
        return Decimal("0")
    return max(Decimal("0"), min(Decimal("1"), Decimal(valor) / Decimal(maximo)))


def recomendar(empresa, oportunidades, perfil=None, contexto=None):
    config = resolver_configuracao(empresa, contexto)
    if config is None:
        raise ValueError("Cadastre uma configuração logística ativa para a empresa.")
    pesos = dict(PESOS_PADRAO)
    for fonte in (config.pesos, perfil.pesos if perfil else {}):
        for chave, valor in fonte.items():
            if chave in pesos:
                pesos[chave] = Decimal(str(valor))
    if contexto and contexto.get("operacao") == "MAXIMIZAR_LUCRO":
        pesos.update({
            "lucro": Decimal("0.70"), "km_vazio": Decimal("0.15"),
            "tempo_espera": Decimal("0.05"), "continuidade": Decimal("0.07"),
            "risco": Decimal("0.03"),
        })

    agora = timezone.now()
    validas, descartadas = [], []
    for item in oportunidades:
        motivos = []
        if item.empresa_id != empresa.id:
            motivos.append("empresa_incompativel")
        if not item.ativo or (item.expira_em and item.expira_em <= agora):
            motivos.append("oportunidade_inativa_ou_expirada")
        if item.parceiro_id and not item.parceiro.ativo:
            motivos.append("parceiro_inativo")
        if item.km_vazio > config.km_vazio_maximo_desejado:
            motivos.append("km_vazio_acima_do_limite")
        if item.lucro_estimado < config.margem_minima_desejada:
            motivos.append("margem_abaixo_do_minimo")
        if contexto and contexto.get("tipo_veiculo") and item.tipo_veiculo and item.tipo_veiculo != contexto["tipo_veiculo"]:
            motivos.append("veiculo_incompativel")
        if contexto and contexto.get("capacidade") and item.capacidade_minima and item.capacidade_minima > Decimal(str(contexto["capacidade"])):
            motivos.append("capacidade_incompativel")
        if motivos:
            descartadas.append({"id": item.id, "motivos": motivos})
            continue
        validas.append(item)
    if not validas:
        raise ValueError("Nenhuma oportunidade atende às regras obrigatórias.")

    max_lucro = max(item.lucro_estimado for item in validas) or Decimal("1")
    alternativas = []
    for item in validas:
        nota = Decimal("100") * (
            pesos["lucro"] * _normalizar(item.lucro_estimado, max_lucro)
            + pesos["km_vazio"] * (Decimal("1") - _normalizar(item.km_vazio, config.km_vazio_maximo_desejado))
            + pesos["tempo_espera"] * (Decimal("1") - _normalizar(item.tempo_espera_horas, config.tempo_espera_maximo_horas))
            + pesos["continuidade"] * item.probabilidade_continuidade
            + pesos["risco"] * (Decimal("1") - item.risco_retorno_vazio)
        )
        lucro_ciclo = item.lucro_estimado + item.lucro_estimado * item.probabilidade_continuidade * Decimal("0.5")
        alternativas.append({
            "oportunidade_id": item.id,
            "score_regras": float(round(nota, 2)),
            "score_final": float(round(nota, 2)),
            "lucro_imediato": float(item.lucro_estimado),
            "lucro_esperado_ciclo": float(round(lucro_ciclo, 2)),
            "probabilidade_continuidade": float(item.probabilidade_continuidade),
            "confianca": "BAIXA",
            "valor_km_carregado": float(round(item.valor_km_carregado, 2)) if item.valor_km_carregado is not None else None,
            "valor_km_com_vazio": float(round(item.valor_km_com_vazio, 2)) if item.valor_km_com_vazio is not None else None,
            "classificacao_km": "RUIM" if item.valor_km_com_vazio is not None and item.valor_km_com_vazio < Decimal("12") else ("BOM" if item.valor_km_com_vazio is not None else "SEM_DISTANCIA"),
        })
    alternativas.sort(key=lambda item: (item["score_final"], item["lucro_esperado_ciclo"]), reverse=True)

    total_historico = ResultadoAprendizadoLogistico.objects.filter(
        empresa=empresa, lucro_real__isnull=False
    ).aggregate(total=Count("id"))["total"]
    modelo = ModeloLogisticoIA.objects.filter(empresa=empresa, status=ModeloLogisticoIA.Status.ATIVO).first()
    avisos = []
    if not config.usar_recomendacoes_ia:
        avisos.append("A empresa optou por operar somente com regras.")
    elif total_historico < config.quantidade_minima_registros_ia:
        avisos.append("Histórico insuficiente; a recomendação utiliza configurações manuais e regras.")
    elif modelo is None:
        avisos.append("Não há modelo validado ativo; aplicado retorno seguro para regras.")
    modo = "REGRAS"
    if config.usar_recomendacoes_ia and total_historico >= config.quantidade_minima_registros_ia and modelo is not None:
        oportunidades_por_id = {item.id: item for item in validas}
        for alternativa in alternativas:
            previsao = prever_lucro(modelo, features_oportunidade(oportunidades_por_id[alternativa["oportunidade_id"]]))
            alternativa["lucro_previsto_ia"] = round(previsao, 2)
            alternativa["confianca"] = "MEDIA" if total_historico < 500 else "ALTA"
        alternativas.sort(key=lambda item: (item["lucro_previsto_ia"], item["score_final"]), reverse=True)
        modo = "IA"
    return {
        "recomendada": alternativas[0],
        "alternativas": alternativas,
        "descartadas": descartadas,
        "modo": modo,
        "modelo_versao": modelo.versao if modo == "IA" else None,
        "avisos": avisos,
        "explicacao": [
            "Alternativas incompatíveis foram removidas antes da pontuação.",
            "A nota combina lucro, quilômetros vazios, espera, continuidade e risco com pesos da empresa/perfil.",
            "A decisão final permanece com o operador.",
            *( ["Objetivo selecionado: maximizar o lucro esperado, sem ignorar vazio, espera, continuidade e risco."] if contexto and contexto.get("operacao") == "MAXIMIZAR_LUCRO" else [] ),
        ],
        "objetivo": contexto.get("operacao") if contexto else "EQUILIBRADO",
    }
