from django.db import models
from caminhoes.models import Caminhao  # Motorista pertence a um conjunto
from django.contrib.auth import get_user_model


User = get_user_model()

class Motorista(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name="motoristas")


    nome = models.CharField(max_length=150)
    cpf = models.CharField(max_length=14, unique=True)
    idade = models.PositiveIntegerField()
    venc_cnh = models.DateField()

    # Motorista pertence a um conjunto (cavalo+carretas)
    caminhao = models.ForeignKey(
        Caminhao,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="motoristas"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nome} - {self.cpf}"


class Vale(models.Model):
    motorista = models.ForeignKey(
        Motorista,
        on_delete=models.CASCADE,
        related_name="vales"
    )

    data = models.DateField()
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    pago = models.BooleanField(default=False)

    def __str__(self):
        return f"Vale {self.valor} - {self.motorista.nome}"
