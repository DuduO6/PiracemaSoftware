from django.core.management.base import BaseCommand
from django.db import transaction

from inteligencia_logistica.models import (ConfiguracaoLogisticaEmpresa, Empresa,
                                            LocalLogistico, RotaEstrategica)


class Command(BaseCommand):
    help = "Cria a configuração inicial da Piracema como dados do primeiro tenant."

    @transaction.atomic
    def handle(self, *args, **options):
        empresa, _ = Empresa.objects.get_or_create(slug="piracema-transportes", defaults={"nome": "Piracema Transportes"})
        base, _ = LocalLogistico.objects.get_or_create(
            empresa=empresa, cidade="Piracema", estado="MG", tipo="BASE", defaults={"nome": "Piracema - MG", "prioridade": 100}
        )
        uberlandia, _ = LocalLogistico.objects.get_or_create(
            empresa=empresa, cidade="Uberlândia", estado="MG", tipo="POLO", defaults={"nome": "Uberlândia - MG", "prioridade": 90}
        )
        carmo, _ = LocalLogistico.objects.get_or_create(
            empresa=empresa, cidade="Carmo da Mata", estado="MG", tipo="POLO", defaults={"nome": "Carmo da Mata - MG", "prioridade": 80}
        )
        RotaEstrategica.objects.get_or_create(empresa=empresa, origem=uberlandia, destino=base)
        RotaEstrategica.objects.get_or_create(empresa=empresa, origem=carmo, destino=base)
        ConfiguracaoLogisticaEmpresa.objects.get_or_create(empresa=empresa, nivel="GLOBAL")
        self.stdout.write(self.style.SUCCESS(f"Configuração inicial criada para {empresa.nome} (id={empresa.id})."))
