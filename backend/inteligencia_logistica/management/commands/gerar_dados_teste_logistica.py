from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from inteligencia_logistica.models import (ConfiguracaoLogisticaEmpresa, Empresa,
                                            LocalLogistico, MembroEmpresa,
                                            OportunidadeFrete, ParceiroFrete,
                                            PerfilEstrategia, RotaEstrategica)


OPORTUNIDADES = [
    ("Cooperativa Triângulo", "Uberlândia/MG", "Piracema/MG", "SOJA", 38, 12400, 4650, .86, .12),
    ("Cerealista Mineira", "Carmo da Mata/MG", "Piracema/MG", "MILHO", 22, 8750, 3180, .79, .16),
    ("AgroVale", "Uberaba/MG", "Ribeirão Preto/SP", "FARELO DE SOJA", 64, 14200, 5390, .82, .18),
    ("Grãos do Cerrado", "Catalão/GO", "Uberlândia/MG", "SOJA", 91, 15850, 6140, .76, .24),
    ("Minas Rações", "Patos de Minas/MG", "Contagem/MG", "MILHO", 47, 10900, 4280, .68, .31),
    ("Fertilizantes Brasil", "Araxá/MG", "Rio Verde/GO", "FERTILIZANTE", 73, 17600, 7350, .72, .27),
    ("Calcário Centro-Oeste", "Arcos/MG", "Formiga/MG", "CALCÁRIO", 18, 6200, 2460, .61, .22),
    ("Siderúrgica Horizonte", "Sete Lagoas/MG", "Betim/MG", "BOBINA DE AÇO", 35, 11800, 4970, .57, .38),
    ("Cooperativa Triângulo", "Uberlândia/MG", "Goiânia/GO", "MILHO", 12, 9800, 3620, .88, .10),
    ("AgroVale", "Ribeirão Preto/SP", "Uberaba/MG", "AÇÚCAR", 106, 16900, 7010, .66, .33),
    ("Laticínios Serra", "Divinópolis/MG", "Belo Horizonte/MG", "LEITE EM PÓ", 29, 7600, 2940, .73, .19),
    ("Madeiras Nobre", "João Pinheiro/MG", "Campinas/SP", "MADEIRA", 118, 21300, 9620, .52, .46),
    ("Cimento Nacional", "Pedro Leopoldo/MG", "Uberaba/MG", "CIMENTO", 55, 13250, 5160, .71, .25),
    ("Cerealista Mineira", "Carmo da Mata/MG", "Lavras/MG", "CAFÉ", 16, 9150, 3270, .84, .13),
    ("Grãos do Cerrado", "Rio Verde/GO", "Santos/SP", "SOJA", 145, 28700, 13200, .63, .41),
]


class Command(BaseCommand):
    help = "Gera dados locais idempotentes de Inteligência Logística para um usuário."

    def add_arguments(self, parser):
        parser.add_argument("--usuario", default="dudu")

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        usuario = User.objects.filter(username__iexact=options["usuario"]).first()
        if not usuario:
            raise CommandError(f"Usuário {options['usuario']!r} não encontrado.")

        empresa, _ = Empresa.objects.get_or_create(
            slug="piracema-transportes", defaults={"nome": "Piracema Transportes"}
        )
        MembroEmpresa.objects.update_or_create(
            empresa=empresa, usuario=usuario, defaults={"papel": "ADMIN", "ativo": True}
        )
        locais = {}
        for nome, cidade, tipo, prioridade in (
            ("Piracema - MG", "Piracema", "BASE", 100),
            ("Uberlândia - MG", "Uberlândia", "POLO", 90),
            ("Carmo da Mata - MG", "Carmo da Mata", "POLO", 80),
        ):
            locais[cidade], _ = LocalLogistico.objects.update_or_create(
                empresa=empresa, cidade=cidade, estado="MG", tipo=tipo,
                defaults={"nome": nome, "prioridade": prioridade, "ativo": True},
            )
        for origem in (locais["Uberlândia"], locais["Carmo da Mata"]):
            RotaEstrategica.objects.get_or_create(empresa=empresa, origem=origem, destino=locais["Piracema"])

        ConfiguracaoLogisticaEmpresa.objects.update_or_create(
            empresa=empresa, nivel="GLOBAL", operacao="", caminhao_id=None, carreta_id=None,
            decisao_referencia="", defaults={
                "raio_padrao_busca_km": 180, "km_vazio_maximo_desejado": 160,
                "tempo_espera_maximo_horas": 36, "margem_minima_desejada": 1500,
                "custo_medio_hora_parada": 85, "custo_manutencao_por_km": Decimal("0.42"),
                "custo_pneu_por_km": Decimal("0.18"), "usar_recomendacoes_ia": False,
                "pesos": {"lucro": .45, "km_vazio": .2, "tempo_espera": .1, "continuidade": .2, "risco": .05},
                "ativo": True,
            },
        )
        perfis = {
            "Conservador": {"lucro": .25, "km_vazio": .3, "tempo_espera": .15, "continuidade": .15, "risco": .15},
            "Rentabilidade": {"lucro": .6, "km_vazio": .1, "tempo_espera": .05, "continuidade": .2, "risco": .05},
            "Redução de Vazio": {"lucro": .2, "km_vazio": .55, "tempo_espera": .05, "continuidade": .15, "risco": .05},
        }
        for nome, pesos in perfis.items():
            PerfilEstrategia.objects.update_or_create(
                empresa=empresa, nome=nome, defaults={"tipo": "PERSONALIZADO", "pesos": pesos, "ativo": True}
            )

        parceiros = {}
        for indice, nome in enumerate(sorted({item[0] for item in OPORTUNIDADES})):
            parceiros[nome], _ = ParceiroFrete.objects.update_or_create(
                empresa=empresa, nome=nome,
                defaults={"confiabilidade": Decimal("0.55") + Decimal(indice % 5) * Decimal("0.08"), "ativo": True},
            )

        agora = timezone.now()
        for indice, (cliente, origem, destino, carga, vazio, receita, custo, continuidade, risco) in enumerate(OPORTUNIDADES):
            OportunidadeFrete.objects.update_or_create(
                empresa=empresa, parceiro=parceiros[cliente], origem=origem, destino=destino, tipo_carga=carga,
                defaults={
                    "tipo_veiculo": "GRANELEIRO" if carga in {"SOJA", "MILHO", "FARELO DE SOJA", "FERTILIZANTE"} else "CARRETA",
                    "capacidade_minima": Decimal("27.00") + Decimal(indice % 4), "receita": receita,
                    "custo_estimado": custo, "km_vazio": vazio, "tempo_espera_horas": 4 + (indice % 7) * 3,
                    "distancia_carregada_km": 260 + (indice % 8) * 70,
                    "probabilidade_continuidade": Decimal(str(continuidade)), "risco_retorno_vazio": Decimal(str(risco)),
                    "expira_em": agora + timedelta(days=3 + indice % 5), "ativo": True,
                    "fonte_nome": "Dados sintéticos de teste", "disponibilidade_confirmada": False,
                },
            )
        self.stdout.write(self.style.SUCCESS(
            f"{len(OPORTUNIDADES)} oportunidades criadas para {usuario.username} na empresa {empresa.nome} (id={empresa.id})."
        ))
