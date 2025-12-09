from django.db import models

class Caminhao(models.Model):
    nome_conjunto = models.CharField(max_length=100, blank=True, null=True)
    placa_cavalo = models.CharField(max_length=10, blank=True, null=True)
    renavam_cavalo = models.CharField(max_length=20, blank=True, null=True)

    marca_modelo = models.CharField(max_length=200, blank=True, null=True)

    crlv_cavalo = models.FileField(upload_to="crlv/", blank=True, null=True)

    qtd_placas = models.PositiveIntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)


class Carreta(models.Model):
    caminhao = models.ForeignKey(Caminhao, related_name="carretas", on_delete=models.CASCADE)

    placa = models.CharField(max_length=10, blank=True, null=True)
    renavam = models.CharField(max_length=20, blank=True, null=True)

    crlv = models.FileField(upload_to="crlv/", blank=True, null=True)
