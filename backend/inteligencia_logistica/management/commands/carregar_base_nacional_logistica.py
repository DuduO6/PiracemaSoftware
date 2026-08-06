from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from inteligencia_logistica.models import (CategoriaPolo, ClassificacaoPolo,
                                            IndicadorFrete, PoloLogisticoNacional,
                                            ProdutoLogistico, TipoVeiculoPermitido)


POLOS = {
    "POLO_SOJA": {
        "MT": ["Sorriso", "Lucas do Rio Verde", "Nova Mutum", "Sinop", "Campo Novo do Parecis", "Primavera do Leste", "Rondonópolis"],
        "GO": ["Rio Verde", "Jataí", "Mineiros", "Cristalina"], "BA": ["Luís Eduardo Magalhães", "Barreiras", "São Desidério"],
        "MA": ["Balsas"], "TO": ["Porto Nacional"], "PR": ["Cascavel", "Toledo", "Maringá", "Londrina"],
        "RS": ["Passo Fundo", "Cruz Alta", "Carazinho"], "MG": ["Uberlândia", "Uberaba", "Patrocínio", "Paracatu", "Unaí"],
    },
    "POLO_SORGO": {"GO": ["Rio Verde", "Jataí", "Mineiros", "Catalão"], "MG": ["Uberlândia", "Uberaba", "Patos de Minas", "Paracatu", "Patrocínio"], "MT": ["Rondonópolis", "Sorriso"]},
    "POLO_FERTILIZANTE": {"PR": ["Paranaguá"], "SP": ["Santos"], "MA": ["Itaqui"], "RS": ["Rio Grande"], "ES": ["Vitória"], "BA": ["Aratu"], "MG": ["Uberaba", "Araxá", "Serra do Salitre", "Uberlândia"], "GO": ["Catalão", "Rio Verde"], "MT": ["Rondonópolis"]},
    "POLO_CALCARIO": {"MG": ["Arcos", "Pains", "Doresópolis", "Formiga", "Sete Lagoas", "Pedro Leopoldo", "Matozinhos"], "GO": ["Catalão", "Cocalzinho de Goiás", "Formosa"], "MS": ["Bodoquena", "Miranda"], "PR": ["Rio Branco do Sul"]},
    "POLO_CIMENTO": {"MG": ["Arcos", "Pedro Leopoldo", "Sete Lagoas", "Matozinhos"], "SP": ["Votorantim", "Cajati", "Salto de Pirapora"], "PR": ["Rio Branco do Sul"], "GO": ["Cocalzinho de Goiás"]},
}
REGIOES = {"AC": "NORTE", "AP": "NORTE", "AM": "NORTE", "PA": "NORTE", "RO": "NORTE", "RR": "NORTE", "TO": "NORTE", "AL": "NORDESTE", "BA": "NORDESTE", "CE": "NORDESTE", "MA": "NORDESTE", "PB": "NORDESTE", "PE": "NORDESTE", "PI": "NORDESTE", "RN": "NORDESTE", "SE": "NORDESTE", "DF": "CENTRO_OESTE", "GO": "CENTRO_OESTE", "MT": "CENTRO_OESTE", "MS": "CENTRO_OESTE", "ES": "SUDESTE", "MG": "SUDESTE", "RJ": "SUDESTE", "SP": "SUDESTE", "PR": "SUL", "RS": "SUL", "SC": "SUL"}
PRODUTOS = {
    "soja": ("Soja", "GRÃOS", True, False), "milho": ("Milho", "GRÃOS", True, False),
    "sorgo": ("Sorgo", "GRÃOS", True, False), "fertilizante-granel": ("Fertilizante granel", "INSUMOS", True, False),
    "fertilizante-ensacado": ("Fertilizante ensacado", "INSUMOS", False, True), "calcario": ("Calcário", "MINERAL", True, False),
    "cimento-granel": ("Cimento granel", "CONSTRUÇÃO", True, False), "cimento-ensacado": ("Cimento ensacado", "CONSTRUÇÃO", False, True),
}
VEICULOS = {
    "soja": ["Rodotrem graneleiro", "Bitrem graneleiro", "Carreta LS graneleira", "Carreta simples graneleira"],
    "milho": ["Rodotrem graneleiro", "Bitrem graneleiro", "Carreta LS graneleira", "Carreta simples graneleira"],
    "sorgo": ["Rodotrem graneleiro", "Bitrem graneleiro", "Carreta LS graneleira", "Carreta simples graneleira"],
    "fertilizante-granel": ["Rodotrem graneleiro", "Bitrem graneleiro", "Basculante"],
    "fertilizante-ensacado": ["Sider", "Baú", "Carga seca"], "calcario": ["Rodotrem basculante", "Bitrem basculante", "Basculante"],
    "cimento-granel": ["Carreta silo", "Bitrem silo"], "cimento-ensacado": ["Baú", "Sider", "Carga seca"],
}
INDICADORES = {
    "soja": {"LONGA": (.21, .26, .31), "MEDIA": (.25, .285, .32), "CURTA": (.40, .45, .50)},
    "milho": {"LONGA": (.21, .24, .27), "MEDIA": (.28, .295, .31), "CURTA": (.35, .415, .48)},
    "fertilizante-granel": {"LONGA": (.21, .23, .25), "MEDIA": (.25, .35, .45), "CURTA": (.45, .675, .90)},
    "calcario": {"GERAL": (.20, .425, .65)}, "cimento-granel": {"GERAL": (.25, .40, .55)},
}


class Command(BaseCommand):
    help = "Carrega idempotentemente a base nacional inicial de polos, produtos, compatibilidades e indicadores."

    @transaction.atomic
    def handle(self, *args, **options):
        produtos = {}
        for codigo, (nome, categoria, granel, ensacado) in PRODUTOS.items():
            produtos[codigo], _ = ProdutoLogistico.objects.update_or_create(
                codigo=codigo, defaults={"produto": nome, "categoria": categoria, "tipo_carga": nome.upper(), "granel": granel, "ensacado": ensacado, "ativo": True}
            )
            for veiculo in VEICULOS[codigo]:
                TipoVeiculoPermitido.objects.get_or_create(produto=produtos[codigo], tipo_veiculo=veiculo)

        categorias = {}
        for codigo, estados in POLOS.items():
            categorias[codigo], _ = CategoriaPolo.objects.get_or_create(codigo=codigo, defaults={"nome": codigo.replace("POLO_", "").replace("_", " ").title()})
            produto_codigo = {"POLO_SOJA": "soja", "POLO_SORGO": "sorgo", "POLO_FERTILIZANTE": "fertilizante-granel", "POLO_CALCARIO": "calcario", "POLO_CIMENTO": "cimento-granel"}[codigo]
            for uf, cidades in estados.items():
                for cidade in cidades:
                    polo, _ = PoloLogisticoNacional.objects.update_or_create(
                        cidade=cidade, estado=uf, defaults={"nome": f"{cidade}/{uf}", "regiao": REGIOES.get(uf, ""), "nivel_importancia": 3, "ativo": True}
                    )
                    ClassificacaoPolo.objects.get_or_create(
                        polo=polo, categoria=categorias[codigo], produto=produtos[produto_codigo], papel="PRODUZ",
                        defaults={"probabilidade_referencia": Decimal("0.70"), "fonte": "Base nacional inicial; validar com CONAB/ANM e histórico da empresa"},
                    )
        categoria_milho, _ = CategoriaPolo.objects.get_or_create(codigo="POLO_MILHO", defaults={"nome": "Milho"})
        for classificacao in ClassificacaoPolo.objects.filter(categoria=categorias["POLO_SOJA"]):
            ClassificacaoPolo.objects.get_or_create(polo=classificacao.polo, categoria=categoria_milho, produto=produtos["milho"], papel="PRODUZ", defaults={"probabilidade_referencia": Decimal("0.65"), "fonte": "Base nacional inicial; validar com CONAB e histórico da empresa"})

        for produto_codigo, faixas in INDICADORES.items():
            for distancia, valores in faixas.items():
                IndicadorFrete.objects.update_or_create(
                    produto=produtos[produto_codigo], origem_regiao="BRASIL", destino_regiao="BRASIL", faixa_distancia=distancia, tipo_veiculo="",
                    defaults={"faixa_minima_tkm": valores[0], "faixa_media_tkm": valores[1], "faixa_maxima_tkm": valores[2], "ultima_atualizacao": date(2026, 8, 6), "fonte": "Referência inicial fornecida no requisito; não representa cotação atual", "nivel_confianca": "BAIXA"},
                )
        self.stdout.write(self.style.SUCCESS(f"Base carregada: {PoloLogisticoNacional.objects.count()} polos, {ProdutoLogistico.objects.count()} produtos e {IndicadorFrete.objects.count()} indicadores."))
