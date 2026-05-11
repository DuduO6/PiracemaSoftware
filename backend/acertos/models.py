from django.db import models
from django.conf import settings
from motoristas.models import Motorista, Vale
from viagens.models import Viagem
from decimal import Decimal


class RegraAcerto(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="regras_acerto",
    )
    nome = models.CharField(max_length=120)
    percentual_comissao = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("13.00"))
    aplicar_vales_pendentes = models.BooleanField(default=True)
    desconto_fixo = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    ativo = models.BooleanField(default=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-ativo", "-data_atualizacao"]

    def __str__(self):
        return self.nome


class Acerto(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    motorista = models.ForeignKey(Motorista, on_delete=models.CASCADE)
    data_inicio = models.DateField()
    data_fim = models.DateField()
    data_geracao = models.DateTimeField(auto_now_add=True)
    
    total_viagens = models.IntegerField()
    valor_total_viagens = models.DecimalField(max_digits=10, decimal_places=2)
    total_viagens_com_cte = models.IntegerField(default=0)
    valor_total_viagens_com_cte = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total_viagens_sem_cte = models.IntegerField(default=0)
    valor_total_viagens_sem_cte = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    desconto_cte = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total_vales = models.DecimalField(max_digits=10, decimal_places=2)
    comissao = models.DecimalField(max_digits=10, decimal_places=2)
    valor_a_receber = models.DecimalField(max_digits=10, decimal_places=2)
    desconto_fixo = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    desconto_vales = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    percentual_comissao = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("13.00"))
    regra_aplicada = models.ForeignKey(
        RegraAcerto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acertos",
    )
    
    observacoes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-data_geracao']

    def __str__(self):
        return f"Acerto {self.motorista.nome} - {self.data_inicio} a {self.data_fim}"


class ItemAcerto(models.Model):
    """Armazena cada viagem incluída no acerto"""
    acerto = models.ForeignKey(Acerto, on_delete=models.CASCADE, related_name='itens')
    viagem = models.ForeignKey(Viagem, on_delete=models.CASCADE)
    
    # Duplicamos os dados da viagem para manter histórico mesmo se ela for editada
    data = models.DateField()
    origem = models.CharField(max_length=255)
    destino = models.CharField(max_length=255)
    cliente = models.CharField(max_length=255)
    peso = models.DecimalField(max_digits=10, decimal_places=2)
    valor_tonelada = models.DecimalField(max_digits=10, decimal_places=2)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2)
    teve_cte = models.BooleanField(default=False)
    valor_desconto_cte = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    pago = models.BooleanField()

    def __str__(self):
        return f"{self.data} - {self.cliente}"


class ValeAcerto(models.Model):
    """Armazena cada vale incluído no acerto"""
    acerto = models.ForeignKey(Acerto, on_delete=models.CASCADE, related_name='vales')
    vale = models.ForeignKey(Vale, on_delete=models.CASCADE)
    
    # Duplicamos os dados do vale
    data = models.DateField()
    valor_original = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    valor_restante = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    quitado = models.BooleanField(default=False)

    def __str__(self):
        return f"Vale {self.data} - R$ {self.valor}"
