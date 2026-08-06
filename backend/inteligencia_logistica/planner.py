from collections import Counter, defaultdict
from decimal import Decimal
from math import asin, cos, radians, sin, sqrt
import unicodedata

from fretes.services.geocoding_service import GeocodingService
from fretes.services.routing_service import RoutingService
from viagens.models import Viagem
from .models import OportunidadeFrete
from .regioes import REGIOES_LOGISTICAS


def _separar_local(texto, estado_padrao=""):
    partes = [parte.strip() for parte in str(texto or "").replace("/", " - ").split(" - ") if parte.strip()]
    return partes[0], (partes[1][:2].upper() if len(partes) > 1 else estado_padrao)


def _confianca(ocorrencias, total):
    proporcao = ocorrencias / max(total, 1)
    if ocorrencias >= 5 or (ocorrencias >= 3 and proporcao >= .3):
        return "ALTA"
    if ocorrencias >= 2:
        return "MEDIA"
    return "BAIXA"


def _chave_local(texto):
    normalizado = unicodedata.normalize("NFKD", " ".join(str(texto or "").split()))
    return "".join(letra for letra in normalizado if not unicodedata.combining(letra)).casefold()


def _distancia_geografica_km(a, b):
    lat1, lon1 = radians(a["coordenadas"]["lat"]), radians(a["coordenadas"]["lng"])
    lat2, lon2 = radians(b["coordenadas"]["lat"]), radians(b["coordenadas"]["lng"])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 6371 * 2 * asin(sqrt(h))


def planejar_reposicionamento(*, usuario, empresa=None, cidade_atual, estado_atual="MG", destino_pessoal="",
                              estado_destino_pessoal="MG", raio_km=150, modo="AUTOMATICO",
                              local_busca="", estado_local_busca="MG", regiao_busca="",
                              pagina_historico=1, tamanho_pagina_historico=4,
                              geocoder=None, router=None):
    geocoder = geocoder or GeocodingService()
    router = router or RoutingService()
    viagens = list(Viagem.objects.filter(usuario=usuario).order_by("-data"))
    if not viagens:
        raise ValueError("Não há viagens registradas para formar sugestões confiáveis.")

    centro_cidade = local_busca.strip() if modo == "MANUAL" and local_busca.strip() else cidade_atual.strip()
    centro_estado = estado_local_busca if modo == "MANUAL" and local_busca.strip() else estado_atual
    atual = geocoder.geocode(cidade_atual, estado_atual, target="localização atual")
    centro = atual if centro_cidade.casefold() == cidade_atual.strip().casefold() else geocoder.geocode(
        centro_cidade, centro_estado, target="local de busca"
    )
    pessoal = geocoder.geocode(destino_pessoal, estado_destino_pessoal, target="destino pessoal") if destino_pessoal else None

    por_origem = defaultdict(list)
    for viagem in viagens:
        por_origem[_chave_local(viagem.origem)].append(viagem)

    preliminares = []
    regiao = REGIOES_LOGISTICAS.get(regiao_busca) if regiao_busca else None
    if regiao_busca and regiao is None:
        raise ValueError("Região logística inválida.")
    cidades_regiao = {_chave_local(cidade) for cidade in regiao["cidades"]} if regiao else None
    grupos = por_origem.values()
    if cidades_regiao:
        grupos = [grupo for grupo in grupos if _chave_local(_separar_local(grupo[0].origem)[0]) in cidades_regiao]
    grupos_priorizados = sorted(grupos, key=len, reverse=True)[:10]
    for grupo in grupos_priorizados:
        exemplo = grupo[0]
        cidade_origem, uf_origem = _separar_local(exemplo.origem)
        origem = geocoder.geocode(cidade_origem, uf_origem, target="local histórico de carregamento")
        distancia_aproximada = _distancia_geografica_km(centro, origem)
        if distancia_aproximada > float(raio_km) * 1.25:
            continue
        destinos = Counter(_chave_local(item.destino) for item in grupo)
        destino_chave, ocorrencias_destino = destinos.most_common(1)[0]
        destino_nome = next(item.destino.strip() for item in grupo if _chave_local(item.destino) == destino_chave)
        receita_media = sum((item.valor_total for item in grupo), Decimal("0")) / len(grupo)
        pesos = [item.peso for item in grupo if item.peso is not None]
        peso_medio = sum(pesos, Decimal("0")) / len(pesos) if pesos else Decimal("0")
        preliminares.append({
            "origem": origem, "destino_nome": destino_nome,
            "cliente_principal": Counter(item.cliente for item in grupo).most_common(1)[0][0],
            "ocorrencias_origem": len(grupo), "ocorrencias_corredor": ocorrencias_destino,
            "receita_media_historica": float(round(receita_media, 2)),
            "peso_medio_t": float(round(peso_medio, 2)),
            "distancia_aproximada": distancia_aproximada,
            "confianca": _confianca(ocorrencias_destino, len(viagens)),
        })

    preliminares.sort(key=lambda item: (item["distancia_aproximada"], -item["ocorrencias_corredor"]))
    candidatos = []
    direto = router.calculate_route(atual, pessoal, {}) if pessoal else None
    for item in preliminares[:3]:
        cidade_destino, uf_destino = _separar_local(item["destino_nome"])
        destino = geocoder.geocode(cidade_destino, uf_destino, target="destino histórico")
        vazio = router.calculate_route(centro, item["origem"], {})
        if Decimal(str(vazio["distancia_km"])) > Decimal(str(raio_km)):
            continue
        carregada = router.calculate_route(item["origem"], destino, {})
        retorno_pessoal = router.calculate_route(destino, pessoal, {}) if pessoal else None
        desvio_total = float(vazio["distancia_km"])
        if pessoal:
            desvio_total = max(0, float(vazio["distancia_km"]) + float(carregada["distancia_km"]) + float(retorno_pessoal["distancia_km"]) - float(direto["distancia_km"]))
        candidatos.append({
            **{chave: valor for chave, valor in item.items() if chave not in {"distancia_aproximada", "destino_nome"}},
            "destino_historico": destino,
            "km_vazio_ate_carregamento": vazio["distancia_km"],
            "km_rota_historica": carregada["distancia_km"],
            "desvio_estimado_destino_pessoal_km": round(desvio_total, 2) if pessoal else None,
            "geometria_vazio": vazio["geometria_preview"],
            "geometria_carregada": carregada["geometria_preview"],
            "geometria_destino_pessoal": retorno_pessoal["geometria_preview"] if retorno_pessoal else [],
            "fonte": "Histórico privado de viagens da empresa + distâncias rodoviárias OSRM/OpenStreetMap",
            "aviso": "Corredor histórico; confirme disponibilidade, valor e compatibilidade com o parceiro antes de decidir.",
        })
    candidatos.sort(key=lambda item: (
        item["km_vazio_ate_carregamento"],
        item["desvio_estimado_destino_pessoal_km"] if item["desvio_estimado_destino_pessoal_km"] is not None else 0,
        -item["ocorrencias_corredor"],
    ))
    corredores_no_raio = {
        (_chave_local(item["origem"]["cidade"]), _chave_local(item["destino_historico"]["cidade"])): item
        for item in candidatos
    }
    fretes_historicos = []
    for viagem in viagens:
        cidade_origem, _ = _separar_local(viagem.origem)
        cidade_destino, _ = _separar_local(viagem.destino)
        corredor = corredores_no_raio.get((_chave_local(cidade_origem), _chave_local(cidade_destino)))
        if corredor is None:
            continue
        km_carregado = Decimal(str(corredor["km_rota_historica"]))
        km_vazio = Decimal(str(corredor["km_vazio_ate_carregamento"]))
        km_total = km_carregado + km_vazio
        valor_km_carregado = viagem.valor_total / km_carregado if km_carregado else None
        valor_km_com_vazio = viagem.valor_total / km_total if km_total else None
        fretes_historicos.append({
            "viagem_id": viagem.id, "data": viagem.data.isoformat(), "origem": viagem.origem,
            "destino": viagem.destino, "cliente": viagem.cliente, "peso_t": float(viagem.peso),
            "valor_tonelada": float(viagem.valor_tonelada), "valor_total": float(viagem.valor_total),
            "teve_cte": viagem.teve_cte, "numero_cte": viagem.numero_cte, "pago": viagem.pago,
            "km_vazio_calculado": float(round(km_vazio, 2)), "km_carregado_estimado": float(round(km_carregado, 2)),
            "valor_km_carregado": float(round(valor_km_carregado, 2)) if valor_km_carregado is not None else None,
            "valor_km_com_vazio": float(round(valor_km_com_vazio, 2)) if valor_km_com_vazio is not None else None,
            "classificacao": "BOM" if valor_km_com_vazio is not None and valor_km_com_vazio >= Decimal("12") else "RUIM",
        })
    oportunidades_adequadas = []
    if empresa is not None:
        vazio_por_origem = {
            _chave_local(item["origem"]["cidade"]): Decimal(str(item["km_vazio_ate_carregamento"]))
            for item in candidatos
        }
        for oportunidade in OportunidadeFrete.objects.filter(empresa=empresa, ativo=True).select_related("parceiro"):
            chave_origem = _chave_local(_separar_local(oportunidade.origem)[0])
            km_vazio_real = vazio_por_origem.get(chave_origem)
            if km_vazio_real is None or km_vazio_real > Decimal(str(raio_km)):
                continue
            distancia_carregada = oportunidade.distancia_carregada_km
            valor_sem_vazio = oportunidade.receita / distancia_carregada if distancia_carregada else None
            distancia_operacional = (distancia_carregada or 0) + km_vazio_real
            valor_com_vazio = oportunidade.receita / distancia_operacional if distancia_operacional else None
            classificacao = "SEM_DISTANCIA"
            if valor_com_vazio is not None:
                classificacao = "BOM" if valor_com_vazio >= Decimal("12") else "RUIM"
            oportunidades_adequadas.append({
                "oportunidade_id": oportunidade.id,
                "km_vazio_calculado": float(round(km_vazio_real, 2)),
                "valor_km_carregado": float(round(valor_sem_vazio, 2)) if valor_sem_vazio is not None else None,
                "valor_km_com_vazio": float(round(valor_com_vazio, 2)) if valor_com_vazio is not None else None,
                "classificacao": classificacao,
            })
        oportunidades_adequadas.sort(key=lambda item: (
            item["valor_km_com_vazio"] or 0, -item["km_vazio_calculado"]
        ), reverse=True)
    total_fretes_historicos = len(fretes_historicos)
    inicio_historico = (pagina_historico - 1) * tamanho_pagina_historico
    fim_historico = inicio_historico + tamanho_pagina_historico
    return {
        "modo": modo, "raio_km": float(raio_km), "regiao_busca": regiao_busca,
        "regiao_nome": regiao["nome"] if regiao else "Todas as regiões", "localizacao_atual": atual,
        "centro_busca": centro, "destino_pessoal": pessoal, "total_viagens_analisadas": len(viagens),
        "sugestoes": candidatos[:8],
        "fretes_historicos": fretes_historicos[inicio_historico:fim_historico],
        "fretes_historicos_paginacao": {
            "pagina": pagina_historico, "tamanho_pagina": tamanho_pagina_historico,
            "total": total_fretes_historicos, "tem_proxima": fim_historico < total_fretes_historicos,
        },
        "oportunidades_adequadas": oportunidades_adequadas,
        "metodologia": "Os candidatos vêm de origens reais do histórico. O ranking minimiza o vazio rodoviário e, quando informado, estima o desvio até o destino pessoal.",
        "limitacoes": [
            "Não representa oferta de carga em tempo real.",
            "A confiança mede repetição no histórico, não garantia de nova carga.",
            "Confirme carga, preço, janela, jornada e restrições antes da contratação.",
        ],
    }
