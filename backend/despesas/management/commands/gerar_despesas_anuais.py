from django.core.management.base import BaseCommand
from django.utils import timezone
from despesas.models import FuncionarioDespesa, Despesa, CategoriaDespesa
from datetime import date

class Command(BaseCommand):
    help = "Gera despesas mensais para o ano (salários diluídos)."

    def add_arguments(self, parser):
        parser.add_argument('--ano', type=int, default=timezone.now().year)
        parser.add_argument('--usuario', type=int, required=False, help='ID de usuário para filtrar')

    def handle(self, *args, **options):
        ano = options['ano']
        usuario_id = options.get('usuario')

        funcs = FuncionarioDespesa.objects.filter(ativo=True)
        if usuario_id:
            funcs = funcs.filter(usuario_id=usuario_id)

        contador = 0
        for f in funcs:
            cat = CategoriaDespesa.objects.filter(usuario=f.usuario, nome='SALARIO').first()
            if not cat:
                self.stdout.write(self.style.WARNING(f"Sem categoria SALARIO para usuário {f.usuario}; pulei {f}"))
                continue
            f.gerar_despesas_salariais_ano(ano=ano, categoria_salario=cat, usuario=f.usuario)
            contador += 12

        self.stdout.write(self.style.SUCCESS(f"Geradas ~{contador} despesas salariais para {ano}"))
