import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from inteligencia_logistica.models import PracaPedagio, TarifaPedagio


class Command(BaseCommand):
    help = "Importa/atualiza praças e tarifas de um arquivo JSON normalizado de fonte pública."

    def add_arguments(self, parser):
        parser.add_argument("arquivo", help="Arquivo JSON contendo uma lista de praças")
        parser.add_argument("--fonte", required=True, help="URL ou identificação da publicação pública")
        parser.add_argument("--versao", default="", help="Versão/data da publicação")

    def handle(self, *args, **options):
        caminho = Path(options["arquivo"])
        if not caminho.is_file():
            raise CommandError(f"Arquivo não encontrado: {caminho}")
        try:
            registros = json.loads(caminho.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CommandError(f"JSON inválido: {exc}") from exc
        if not isinstance(registros, list):
            raise CommandError("O JSON deve conter uma lista de praças.")

        total_pracas = total_tarifas = 0
        for item in registros:
            obrigatorios = ("nome", "rodovia", "concessionaria", "latitude", "longitude")
            ausentes = [campo for campo in obrigatorios if item.get(campo) in (None, "")]
            if ausentes:
                raise CommandError(f"Praça sem campos obrigatórios: {', '.join(ausentes)}")
            praca, _ = PracaPedagio.objects.update_or_create(
                rodovia=item["rodovia"], praca=item["nome"], concessionaria=item["concessionaria"],
                defaults={
                    "km": item.get("km"), "latitude": item["latitude"], "longitude": item["longitude"],
                    "cidade": item.get("cidade") or "", "estado": item.get("estado") or "",
                    "sentido": item.get("sentido") or "", "categoria": item.get("categoria") or "",
                    "fonte": options["fonte"], "vigencia_inicio": item.get("vigencia_inicio", "2000-01-01"), "ativo": True,
                },
            )
            total_pracas += 1
            for tarifa in item.get("tarifas", []):
                TarifaPedagio.objects.update_or_create(
                    pedagio=praca, quantidade_eixos=tarifa["quantidade_eixos"], vigencia=tarifa["vigencia"],
                    defaults={"valor": tarifa["valor"], "fonte": tarifa.get("fonte", options["fonte"]), "versao": options["versao"]},
                )
                total_tarifas += 1
        self.stdout.write(self.style.SUCCESS(f"Sincronização concluída: {total_pracas} praças e {total_tarifas} tarifas."))
