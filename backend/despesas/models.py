from decimal import Decimal
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.utils import timezone

User = get_user_model()
from caminhoes.models import Caminhao
from motoristas.models import Motorista


# ==============================================================================
# CATEGORIA DE DESPESA
# ==============================================================================

class CategoriaDespesa(models.Model):
    CATEGORIA_CHOICES = [
        ('IPVA', 'IPVA'),
        ('SEGURO', 'Seguro'),
        ('LICENCIAMENTO', 'Licenciamento'),
        ('RASTREADOR', 'Rastreador'),
        ('SALARIO', 'Salário Motorista'),
        ('COMISSAO', 'Comissão Motorista'),
        ('MANUTENCAO', 'Manutenção'),
        ('MULTA', 'Multa'),
        ('GUINCHO', 'Guincho'),
        ('FRANQUIA_SEGURO', 'Franquia de Seguro'),
        ('OUTROS', 'Outros'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='categorias_despesa')
    nome = models.CharField(max_length=100, choices=CATEGORIA_CHOICES)
    descricao = models.TextField(blank=True, null=True)
    cor = models.CharField(max_length=7, default='#6366F1')

    class Meta:
        unique_together = ['usuario', 'nome']
        ordering = ['nome']

    def __str__(self):
        return self.get_nome_display()
    
    


# ==============================================================================
# DESPESA (LANÇAMENTO ÚNICO)
# ==============================================================================

def competencia_padrao():
        hoje = timezone.now().date()
        return hoje.replace(day=1)

class Despesa(models.Model):
    """
    Representa um lançamento único de despesa.
    Cada despesa é independente e criada manualmente.
    """
    
    TIPO_CHOICES = [
        ('OPERACIONAL', 'Custo Operacional'),
        ('EVENTUAL', 'Despesa Eventual'),
    ]
    
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('PAGO', 'Pago'),
    ]
    
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='despesas')
    categoria = models.ForeignKey(
        CategoriaDespesa,
        on_delete=models.PROTECT,
        related_name='despesas'
    )
    
    # Caminhão (opcional para SALARIO e COMISSAO)
    caminhao = models.ForeignKey(
        Caminhao,
        on_delete=models.PROTECT,
        related_name='despesas',
        null=True,
        blank=True,
        help_text='Caminhão relacionado (obrigatório exceto para salários/comissões)'
    )
    
    # Motorista (obrigatório apenas para SALARIO e COMISSAO)
    motorista = models.ForeignKey(
        Motorista,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='despesas',
        help_text='Motorista relacionado (obrigatório para salário/comissão)'
    )
    
    descricao = models.CharField(max_length=255)
    observacoes = models.TextField(blank=True, null=True)
    
    # Tipo
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='OPERACIONAL')
    
    # Valor
    valor = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        default=Decimal('0.00'),
        help_text='Valor da despesa'
    )
    
    # Competência (mês/ano de referência)
    competencia = models.DateField(
        default=competencia_padrao,
        help_text='Mês de referência (formato: YYYY-MM-01)'
    )
    
    # Status de pagamento
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDENTE')
    data_pagamento = models.DateField(null=True, blank=True)
    
    # Data de vencimento (opcional)
    data_vencimento = models.DateField(
        null=True,
        blank=True,
        help_text='Data de vencimento da despesa'
    )
    
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-competencia', '-data_cadastro']
        indexes = [
            models.Index(fields=['usuario', 'caminhao', 'tipo']),
            models.Index(fields=['categoria', 'status']),
            models.Index(fields=['competencia', 'status']),
        ]

    def __str__(self):
        if self.caminhao:
            return f"{self.descricao} - {self.caminhao.nome_conjunto} - R$ {self.valor}"
        elif self.motorista:
            return f"{self.descricao} - {self.motorista.nome} - R$ {self.valor}"
        return f"{self.descricao} - R$ {self.valor}"
    
    def marcar_pago(self):
        """Marca despesa como paga."""
        self.status = 'PAGO'
        self.data_pagamento = timezone.now().date()
        self.save()
    
    def marcar_pendente(self):
        """Marca despesa como pendente."""
        self.status = 'PENDENTE'
        self.data_pagamento = None
        self.save()