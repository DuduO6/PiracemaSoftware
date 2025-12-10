from django.db import models
from django.conf import settings  # Importar settings
from motoristas.models import Motorista, Vale

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
    peso = models.DecimalField(max_digits=10, decimal_places=2)
    valor_tonelada = models.DecimalField(max_digits=10, decimal_places=2)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    pago = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        self.valor_total = self.peso * self.valor_tonelada
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.data} - {self.cliente} - {self.motorista.nome}"
