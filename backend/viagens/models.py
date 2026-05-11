from django.db import models
from django.conf import settings  # Importar settings
from motoristas.models import Motorista, Vale
from decimal import Decimal, ROUND_HALF_UP


CASAS_DECIMAIS = Decimal("0.01")
DESCONTO_CTE = Decimal("0.90")

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
        valor = self.peso * self.valor_tonelada
        if self.teve_cte:
            valor *= DESCONTO_CTE
        return valor.quantize(CASAS_DECIMAIS, rounding=ROUND_HALF_UP)

    def save(self, *args, **kwargs):
        self.valor_total = self.calcular_valor_total()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.data} - {self.cliente} - {self.motorista.nome}"
