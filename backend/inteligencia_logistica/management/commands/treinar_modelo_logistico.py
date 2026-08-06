from django.core.management.base import BaseCommand, CommandError

from inteligencia_logistica.ml import treinar_modelo_lucro
from inteligencia_logistica.models import Empresa


class Command(BaseCommand):
    help = "Treina o modelo de lucro usando somente resultados reais auditados."

    def add_arguments(self, parser):
        parser.add_argument("empresa_id", type=int)
        parser.add_argument("--minimo", type=int, default=30)

    def handle(self, *args, **options):
        try:
            empresa = Empresa.objects.get(id=options["empresa_id"], ativo=True)
            modelo = treinar_modelo_lucro(empresa, minimo_registros=options["minimo"])
        except (Empresa.DoesNotExist, ValueError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(
            f"Modelo {modelo.versao} ativado com {modelo.quantidade_registros} resultados; MAE de validação {modelo.metricas['mae_validacao']}."
        ))
