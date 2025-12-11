from decimal import Decimal
from django.db import models, transaction
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.utils import timezone
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta


User = get_user_model()

# IMPORTAÇÃO CORRETA DO SEU MODELO
from caminhoes.models import Caminhao   # ajuste se o nome da app for diferente


class CategoriaDespesa(models.Model):
    CATEGORIA_CHOICES = [
        ('IPVA', 'IPVA'),
        ('SEGURO', 'Seguro'),
        ('MANUTENCAO', 'Manutenção'),
        ('ABASTECIMENTO', 'Abastecimento'),
        ('SALARIO', 'Salário'),
        ('COMISSAO', 'Comissão'),
        ('LICENCIAMENTO', 'Licenciamento'),
        ('PEDAGIO', 'Pedágio'),
        ('MULTA', 'Multa'),
        ('OUTROS', 'Outros'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='categorias_despesa')
    nome = models.CharField(max_length=100, choices=CATEGORIA_CHOICES)
    descricao = models.TextField(blank=True, null=True)
    cor = models.CharField(max_length=7, default='#6366F1')

    class Meta:
        unique_together = ['usuario', 'nome']

    def __str__(self):
        return self.get_nome_display()

class Despesa(models.Model):
    TIPO_CHOICES = [
        ('FIXA', 'Fixa (Parcelada/Diluída)'),
        ('VARIAVEL', 'Variável'),
        ('RECORRENTE', 'Recorrente Mensal'),
    ]

    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('PAGO', 'Pago'),
        ('VENCIDO', 'Vencido'),
        ('CANCELADO', 'Cancelado'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='despesas')
    categoria = models.ForeignKey(CategoriaDespesa, on_delete=models.PROTECT, related_name='despesas')

    # AQUI O CAMPO DE CAMINHÃO FOI CORRIGIDO PARA O SEU MODELO REAL
    caminhao = models.ForeignKey(
        Caminhao,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='despesas',
        help_text='Caminhão relacionado (opcional)'
    )

    descricao = models.CharField(max_length=255)
    observacoes = models.TextField(blank=True, null=True)

    valor_total = models.DecimalField(max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))])

    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='VARIAVEL')

    data_vencimento = models.DateField()
    data_pagamento = models.DateField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDENTE')

    despesa_pai = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True,
        related_name='parcelas'
    )
    numero_parcela = models.IntegerField(null=True, blank=True)
    total_parcelas = models.IntegerField(default=1)

    comprovante = models.FileField(upload_to='despesas/comprovantes/', blank=True, null=True)

    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-data_vencimento', '-data_cadastro']

    def __str__(self):
        return f"{self.descricao} — R$ {self.valor_total}"

    @property
    def valor_mensal(self):
        if self.tipo == 'FIXA' and self.despesa_pai is None:
            parcelas = self.total_parcelas or 12
            return (self.valor_total / parcelas).quantize(Decimal("0.01"))
        return self.valor_total

    @property
    def esta_vencida(self):
        return self.status != "PAGO" and self.data_vencimento < timezone.now().date()

    def save(self, *args, **kwargs):
        if self.esta_vencida and self.status == "PENDENTE":
            self.status = "VENCIDO"
        if self.status == "PAGO" and not self.data_pagamento:
            self.data_pagamento = timezone.now().date()
        super().save(*args, **kwargs)

    @staticmethod
    def criar_parcelas(usuario, categoria, descricao, valor_total, data_vencimento, 
                      total_parcelas, caminhao=None, observacoes="", tipo='FIXA'):
        """
        Cria despesa pai + parcelas automaticamente
        """
        from decimal import Decimal
        
        valor_total_dec = Decimal(str(valor_total))
        valor_parcela = (valor_total_dec / total_parcelas).quantize(Decimal("0.01"))
        
        # Ajuste para garantir que a soma das parcelas = valor total
        diferenca = valor_total_dec - (valor_parcela * total_parcelas)
        
        with transaction.atomic():
            # Cria despesa PAI
            despesa_pai = Despesa.objects.create(
                usuario=usuario,
                categoria=categoria,
                caminhao=caminhao,
                descricao=f"{descricao} (Total)",
                observacoes=observacoes,
                valor_total=valor_total_dec,
                tipo=tipo,
                data_vencimento=data_vencimento,
                status='PENDENTE',
                total_parcelas=total_parcelas
            )
            
            parcelas = []
            for i in range(1, total_parcelas + 1):
                # Calcula data de vencimento de cada parcela (mês a mês)
                data_parcela = data_vencimento + relativedelta(months=i-1)
                
                # Ajusta última parcela para compensar diferença de centavos
                valor_desta_parcela = valor_parcela
                if i == total_parcelas and diferenca != 0:
                    valor_desta_parcela += diferenca
                
                parcela = Despesa.objects.create(
                    usuario=usuario,
                    categoria=categoria,
                    caminhao=caminhao,
                    descricao=descricao,
                    observacoes=observacoes,
                    valor_total=valor_desta_parcela,
                    tipo=tipo,
                    data_vencimento=data_parcela,
                    status='PENDENTE',
                    despesa_pai=despesa_pai,
                    numero_parcela=i,
                    total_parcelas=total_parcelas
                )
                parcelas.append(parcela)
            
            return despesa_pai, parcelas

class FuncionarioDespesa(models.Model):
    """
    Funcionário com salário + comissão (para gerar despesas mensais)
    """
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='funcionarios_despesa')
    nome = models.CharField(max_length=150)
    cargo = models.CharField(max_length=100)

    salario_base = models.DecimalField(max_digits=12, decimal_places=2)
    
    tipo_comissao = models.CharField(
        max_length=20,
        choices=[
            ('PERCENTUAL', 'Percentual sobre viagens'),
            ('FIXA', 'Valor fixo mensal'),
            ('POR_VIAGEM', 'Por viagem realizada'),
        ],
        default='PERCENTUAL'
    )
    valor_comissao = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    ativo = models.BooleanField(default=True)
    data_admissao = models.DateField()
    data_demissao = models.DateField(null=True, blank=True)

    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.nome} - {self.cargo}"
