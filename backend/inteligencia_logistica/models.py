from django.conf import settings
from django.db import models


class Empresa(models.Model):
    """Empresa compartilhada pelo MDF-e e demais módulos multiempresa."""

    nome = models.CharField(max_length=160)
    slug = models.SlugField(unique=True)
    usuarios = models.ManyToManyField(settings.AUTH_USER_MODEL, through="MembroEmpresa")
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome


class MembroEmpresa(models.Model):
    class Papel(models.TextChoices):
        ADMIN = "ADMIN", "Administrador"
        OPERADOR = "OPERADOR", "Operador"
        LEITURA = "LEITURA", "Somente leitura"

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="membros")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="empresas_logisticas")
    papel = models.CharField(max_length=16, choices=Papel.choices, default=Papel.OPERADOR)
    ativo = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("empresa", "usuario"), name="membro_empresa_unico")]


class PracaPedagio(models.Model):
    """Infraestrutura compartilhada pela calculadora de fretes."""

    rodovia = models.CharField(max_length=40)
    praca = models.CharField(max_length=120)
    concessionaria = models.CharField(max_length=160)
    km = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    cidade = models.CharField(max_length=120, blank=True)
    estado = models.CharField(max_length=2, blank=True)
    sentido = models.CharField(max_length=40, blank=True)
    categoria = models.CharField(max_length=60, blank=True)
    tarifas_por_eixo = models.JSONField(default=dict)
    vigencia_inicio = models.DateField()
    vigencia_fim = models.DateField(null=True, blank=True)
    fonte = models.CharField(max_length=300)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.praca} - {self.rodovia}"


class TarifaPedagio(models.Model):
    pedagio = models.ForeignKey(PracaPedagio, on_delete=models.CASCADE, related_name="tarifas")
    quantidade_eixos = models.PositiveSmallIntegerField()
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    vigencia = models.DateField()
    fonte = models.CharField(max_length=500)
    versao = models.CharField(max_length=80, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=("pedagio", "quantidade_eixos", "vigencia"), name="tarifa_pedagio_eixo_vigencia_unica"
        )]
        indexes = [models.Index(fields=("quantidade_eixos", "vigencia"))]


class RouteCache(models.Model):
    chave = models.CharField(max_length=64, unique=True)
    origem = models.JSONField()
    destino = models.JSONField()
    provider = models.CharField(max_length=40)
    distancia_metros = models.PositiveBigIntegerField()
    tempo_segundos = models.PositiveIntegerField()
    pedagios = models.JSONField(default=list)
    geometria = models.JSONField(default=list)
    resposta = models.JSONField(default=dict)
    data_consulta = models.DateTimeField(auto_now=True)
    valido_ate = models.DateTimeField()

    class Meta:
        indexes = [models.Index(fields=("provider", "valido_ate"))]
