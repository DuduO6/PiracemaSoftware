from decimal import Decimal
from django.db import models, transaction
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.utils import timezone
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta


User = get_user_model()
from caminhoes.models import Caminhao


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
        ('FIXA_ANUAL', 'Fixa Anual (Diluída em 12 meses)'),  # IPVA, Seguro, Licenciamento
        ('FIXA_MENSAL', 'Fixa Mensal (Salário)'),            # Salários
        ('VARIAVEL', 'Variável'),                            # Abastecimento, Pedágio, etc
    ]

    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('PAGO', 'Pago'),
        ('VENCIDO', 'Vencido'),
        ('CANCELADO', 'Cancelado'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='despesas')
    categoria = models.ForeignKey(CategoriaDespesa, on_delete=models.PROTECT, related_name='despesas')
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
    valor_total = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )

    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='VARIAVEL')
    
    # Para despesas FIXA_ANUAL: guarda o ano de referência (ex: 2025)
    ano_referencia = models.IntegerField(null=True, blank=True, help_text='Ano da despesa fixa')
    
    # Para FIXA_MENSAL e VARIAVEL
    mes_referencia = models.IntegerField(null=True, blank=True, help_text='Mês (1-12)')
    
    data_vencimento = models.DateField()
    data_pagamento = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDENTE')

    # Controle de parcelas (para FIXA_ANUAL)
    despesa_pai = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='parcelas_mensais'
    )
    numero_parcela = models.IntegerField(null=True, blank=True)  # 1-12 para FIXA_ANUAL
    total_parcelas = models.IntegerField(default=1)

    comprovante = models.FileField(upload_to='despesas/comprovantes/', blank=True, null=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-data_vencimento', '-data_cadastro']
        indexes = [
            models.Index(fields=['usuario', 'ano_referencia', 'mes_referencia']),
            models.Index(fields=['caminhao', 'tipo']),
        ]

    def __str__(self):
        if self.numero_parcela:
            return f"{self.descricao} ({self.numero_parcela}/{self.total_parcelas}) - R$ {self.valor_total}"
        return f"{self.descricao} - R$ {self.valor_total}"

    @property
    def valor_mensal(self):
        """Retorna o valor que deve aparecer no balanço mensal"""
        return self.valor_total

    @property
    def esta_vencida(self):
        hoje = timezone.now().date()
        return self.status != "PAGO" and self.data_vencimento < hoje

    def save(self, *args, **kwargs):
        # Auto-atualiza status se vencida
        if self.esta_vencida and self.status == "PENDENTE":
            self.status = "VENCIDO"
        
        # Auto-define data de pagamento
        if self.status == "PAGO" and not self.data_pagamento:
            self.data_pagamento = timezone.now().date()
        
        # Auto-extrai mês/ano da data_vencimento
        if self.data_vencimento:
            if not self.mes_referencia:
                self.mes_referencia = self.data_vencimento.month
            if not self.ano_referencia and self.tipo == 'FIXA_ANUAL':
                self.ano_referencia = self.data_vencimento.year
        
        super().save(*args, **kwargs)


    @staticmethod
    def criar_despesa_fixa_anual(usuario, categoria, descricao, valor_total, 
                             data_inicio, caminhao=None, observacoes=""):

        """
        Cria uma despesa fixa anual (IPVA, Seguro, etc) e divide em 12 parcelas mensais
        
        Args:
            usuario: User
            categoria: CategoriaDespesa
            descricao: str (ex: "IPVA 2025")
            valor_total: Decimal (ex: 1200.00)
            ano: int (ex: 2025)
            caminhao: Caminhao (opcional)
            observacoes: str
        
        Returns:
            tuple: (despesa_pai, lista_de_parcelas)
        """
        valor_total_dec = Decimal(str(valor_total))
        valor_mensal = (valor_total_dec / 12).quantize(Decimal("0.01"))
        
        # Ajuste para garantir soma exata
        diferenca = valor_total_dec - (valor_mensal * 12)
        
        with transaction.atomic():
            # Cria despesa PAI (registro principal)
            data_inicial = data_inicio
            
            despesa_pai = Despesa.objects.create(
                usuario=usuario,
                categoria=categoria,
                caminhao=caminhao,
                descricao=f"{descricao} (Anual)",
                observacoes=observacoes,
                valor_total=valor_total_dec,
                tipo='FIXA_ANUAL',
                ano_referencia=data_inicial.year,
                data_vencimento=data_inicial,
                status='PENDENTE',
                total_parcelas=12
            )
            
            # Cria 12 parcelas mensais
            parcelas = []
            for i in range(12):
                data_parcela = data_inicio + relativedelta(months=i)

                
                # Última parcela compensa diferença de centavos
                valor_desta_parcela = valor_mensal
                if i == 11 and diferenca != 0:  # última parcela
                    valor_desta_parcela += diferenca
                
                parcela = Despesa.objects.create(
                    usuario=usuario,
                    categoria=categoria,
                    caminhao=caminhao,
                    descricao=descricao,
                    observacoes=observacoes,
                    valor_total=valor_desta_parcela,
                    tipo='FIXA_ANUAL',
                    ano_referencia=data_parcela.year,
                    mes_referencia=data_parcela.month,
                    data_vencimento=data_parcela,
                    status='PENDENTE',
                    despesa_pai=despesa_pai,
                    numero_parcela=i + 1,
                    total_parcelas=12
                )
                parcelas.append(parcela)
            
            return despesa_pai, parcelas

    @staticmethod
    def criar_salario_mensal_ano(usuario, categoria_salario, nome_funcionario, 
                                 valor_mensal, ano, caminhao=None):
        """
        Cria 12 despesas de salário (uma por mês) para o ano inteiro
        
        Args:
            usuario: User
            categoria_salario: CategoriaDespesa (deve ser SALARIO)
            nome_funcionario: str
            valor_mensal: Decimal
            ano: int
            caminhao: Caminhao (opcional)
        
        Returns:
            list: lista de 12 despesas criadas
        """
        valor_dec = Decimal(str(valor_mensal))
        despesas = []
        
        with transaction.atomic():
            for mes in range(1, 13):
                # Define vencimento no dia 5 de cada mês
                data_vencimento = date(ano, mes, 5)
                
                despesa = Despesa.objects.create(
                    usuario=usuario,
                    categoria=categoria_salario,
                    caminhao=caminhao,
                    descricao=f"Salário {nome_funcionario}",
                    valor_total=valor_dec,
                    tipo='FIXA_MENSAL',
                    ano_referencia=data_vencimento.year,
                    mes_referencia=mes,
                    data_vencimento=data_vencimento,
                    status='PENDENTE'
                )
                despesas.append(despesa)
        
        return despesas


class FuncionarioDespesa(models.Model):
    """
    Cadastro de funcionários com salário fixo
    """
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='funcionarios_despesa')
    nome = models.CharField(max_length=150)
    cargo = models.CharField(max_length=100)
    salario_mensal = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Vincula funcionário a um caminhão (opcional)
    caminhao = models.ForeignKey(
        Caminhao, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='funcionarios'
    )
    
    ativo = models.BooleanField(default=True)
    data_admissao = models.DateField()
    data_demissao = models.DateField(null=True, blank=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.nome} - {self.cargo} (R$ {self.salario_mensal})"
    
    def gerar_salarios_ano(self, ano, categoria_salario):
        """
        Gera 12 despesas de salário para o ano
        """
        return Despesa.criar_salario_mensal_ano(
            usuario=self.usuario,
            categoria_salario=categoria_salario,
            nome_funcionario=self.nome,
            valor_mensal=self.salario_mensal,
            ano=ano,
            caminhao=self.caminhao
        )