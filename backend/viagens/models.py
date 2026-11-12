from django.db import models
from django.conf import settings  # Importar settings
from motoristas.models import Motorista, Vale
from decimal import Decimal, ROUND_HALF_UP


CASAS_DECIMAIS = Decimal("0.01")
DESCONTO_CTE = Decimal("0.90")
PERCENTUAL_DESCONTO_CTE = Decimal("0.10")

class Viagem(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # <-- usar AUTH_USER_MODEL
        on_delete=models.CASCADE
    )
    motorista = models.ForeignKey(Motorista, on_delete=models.CASCADE)
    data = models.DateField()
    origem = models.CharField(max_length=255)
    destino = models.CharField(max_length=255)
    cliente = models.CharField(max_length=255)
    teve_cte = models.BooleanField(default=False)
    numero_cte = models.CharField(max_length=32, blank=True, default="")
    peso = models.DecimalField(max_digits=10, decimal_places=2)
    valor_tonelada = models.DecimalField(max_digits=10, decimal_places=2)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    pago = models.BooleanField(default=False)

    def calcular_valor_total(self):
        valor = self.calcular_valor_bruto()
        if self.teve_cte:
            valor *= DESCONTO_CTE
        return valor.quantize(CASAS_DECIMAIS, rounding=ROUND_HALF_UP)

    def calcular_valor_bruto(self):
        return (self.peso * self.valor_tonelada).quantize(CASAS_DECIMAIS, rounding=ROUND_HALF_UP)

    def calcular_desconto_cte(self):
        if not self.teve_cte:
            return Decimal("0.00")
        return (self.calcular_valor_bruto() * PERCENTUAL_DESCONTO_CTE).quantize(CASAS_DECIMAIS, rounding=ROUND_HALF_UP)

    def save(self, *args, **kwargs):
        self.valor_total = self.calcular_valor_total()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.data} - {self.cliente} - {self.motorista.nome}"


class ImportacaoMdfeViagem(models.Model):
    """Rastreabilidade fiscal da origem da viagem, sem duplicar seus dados operacionais."""

    viagem = models.OneToOneField(
        Viagem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="importacao_mdfe",
    )
    empresa = models.ForeignKey(
        "inteligencia_logistica.Empresa",
        on_delete=models.CASCADE,
        related_name="importacoes_viagem_mdfe",
    )
    manifesto = models.ForeignKey(
        "mdfe.Manifesto",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="importacoes_viagem",
    )
    chave_mdfe = models.CharField(max_length=44)
    chave_cte = models.CharField(max_length=44, null=True, blank=True, default=None)
    xml_sha256 = models.CharField(max_length=64, blank=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="importacoes_viagem_mdfe",
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("empresa", "chave_mdfe"),
                name="viagem_import_mdfe_empresa_chave_unica",
            ),
            models.UniqueConstraint(
                fields=("empresa", "chave_cte"),
                name="viagem_import_cte_empresa_chave_unica",
            ),
        ]
        indexes = [models.Index(fields=("empresa", "criado_em"), name="viagem_imp_empresa_data_idx")]

    def __str__(self):
        return f"MDF-e {self.chave_mdfe}"
