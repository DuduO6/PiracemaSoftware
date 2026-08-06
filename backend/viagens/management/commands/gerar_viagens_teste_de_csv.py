import csv
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from motoristas.models import Motorista
from viagens.models import Viagem


class Command(BaseCommand):
    help = "Popula viagens de teste seguindo os padrões de um CSV exportado pelo sistema."

    def add_arguments(self, parser):
        parser.add_argument("arquivo")
        parser.add_argument("--usuario", default="dudu")

    @transaction.atomic
    def handle(self, *args, **options):
        caminho = Path(options["arquivo"])
        if not caminho.is_file():
            raise CommandError(f"Arquivo não encontrado: {caminho}")
        usuario = get_user_model().objects.filter(username__iexact=options["usuario"]).first()
        if not usuario:
            raise CommandError(f"Usuário {options['usuario']!r} não encontrado.")

        criadas = existentes = 0
        motoristas = {}
        with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
            for indice, linha in enumerate(csv.DictReader(arquivo, delimiter=";"), start=1):
                nome_motorista = (linha.get("Motorista") or "Motorista de Teste").strip()
                chave = nome_motorista.casefold()
                if chave not in motoristas:
                    motorista = Motorista.objects.filter(usuario=usuario, nome__iexact=nome_motorista).first()
                    if not motorista:
                        numero = 90000000000 + indice
                        cpf = f"{numero:011d}"
                        cpf = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
                        motorista = Motorista.objects.create(
                            usuario=usuario, nome=nome_motorista, cpf=cpf, idade=35 + indice % 20,
                            venc_cnh=date(2030 + indice % 4, 12, 31),
                        )
                    motoristas[chave] = motorista

                try:
                    data = datetime.strptime(linha["Data"], "%d/%m/%Y").date()
                    peso = Decimal(linha["Peso (TN)"].replace(",", "."))
                    valor_tonelada = Decimal(linha["Valor/TN"].replace(",", "."))
                except (KeyError, ValueError) as exc:
                    raise CommandError(f"Linha {indice + 1} inválida: {exc}") from exc
                teve_cte = (linha.get("Com CTE") or "").strip().casefold() == "sim"
                numero_cte = (linha.get("Numero CTE") or "").strip() if teve_cte else ""
                _, criada = Viagem.objects.get_or_create(
                    usuario=usuario, motorista=motoristas[chave], data=data,
                    origem=(linha.get("Origem") or "").strip(), destino=(linha.get("Destino") or "").strip(),
                    cliente=(linha.get("Cliente") or "Não informado").strip(), peso=peso,
                    valor_tonelada=valor_tonelada, teve_cte=teve_cte, numero_cte=numero_cte,
                    defaults={"pago": (linha.get("Pago") or "").strip().casefold() == "sim"},
                )
                criadas += int(criada)
                existentes += int(not criada)
        self.stdout.write(self.style.SUCCESS(
            f"Viagens de teste para {usuario.username}: {criadas} criadas, {existentes} já existentes; total atual {Viagem.objects.filter(usuario=usuario).count()}."
        ))
