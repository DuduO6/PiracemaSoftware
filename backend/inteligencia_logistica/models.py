from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Empresa(models.Model):
    nome = models.CharField(max_length=160)
    slug = models.SlugField(unique=True)
    usuarios = models.ManyToManyField(settings.AUTH_USER_MODEL, through="MembroEmpresa")
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome


class PoloLogisticoNacional(models.Model):
    class Importancia(models.IntegerChoices):
        REGIONAL = 1, "Regional"
        RELEVANTE = 2, "Relevante"
        ESTRATEGICO = 3, "Estratégico"
        NACIONAL = 4, "Nacional"

    nome = models.CharField(max_length=160)
    cidade = models.CharField(max_length=120)
    estado = models.CharField(max_length=2)
    regiao = models.CharField(max_length=20, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    nivel_importancia = models.PositiveSmallIntegerField(choices=Importancia.choices, default=Importancia.RELEVANTE)
    observacoes = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("cidade", "estado"), name="polo_nacional_cidade_uf_unico")]

    def __str__(self):
        return f"{self.cidade}/{self.estado}"


class CategoriaPolo(models.Model):
    codigo = models.CharField(max_length=40, unique=True)
    nome = models.CharField(max_length=100)
    polos = models.ManyToManyField(PoloLogisticoNacional, through="ClassificacaoPolo", related_name="categorias")

    def __str__(self):
        return self.nome


class ProdutoLogistico(models.Model):
    codigo = models.SlugField(unique=True)
    produto = models.CharField(max_length=100)
    categoria = models.CharField(max_length=80)
    descricao = models.TextField(blank=True)
    tipo_carga = models.CharField(max_length=80)
    temperatura_controlada = models.BooleanField(default=False)
    granel = models.BooleanField(default=False)
    paletizado = models.BooleanField(default=False)
    ensacado = models.BooleanField(default=False)
    bigbag = models.BooleanField(default=False)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.produto


class ClassificacaoPolo(models.Model):
    class Papel(models.TextChoices):
        PRODUZ = "PRODUZ", "Produz"
        CONSOME = "CONSOME", "Consome"
        DISTRIBUI = "DISTRIBUI", "Distribui"
        INDUSTRIALIZA = "INDUSTRIALIZA", "Industrializa"
        IMPORTA = "IMPORTA", "Importa"
        EXPORTA = "EXPORTA", "Exporta"

    polo = models.ForeignKey(PoloLogisticoNacional, on_delete=models.CASCADE, related_name="classificacoes")
    categoria = models.ForeignKey(CategoriaPolo, on_delete=models.CASCADE)
    produto = models.ForeignKey(ProdutoLogistico, on_delete=models.SET_NULL, null=True, blank=True)
    papel = models.CharField(max_length=16, choices=Papel.choices, default=Papel.PRODUZ)
    probabilidade_referencia = models.DecimalField(max_digits=5, decimal_places=4, default=0)
    fonte = models.CharField(max_length=300, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("polo", "categoria", "produto", "papel"), name="classificacao_polo_unica")]


class TipoVeiculoPermitido(models.Model):
    produto = models.ForeignKey(ProdutoLogistico, on_delete=models.CASCADE, related_name="veiculos_permitidos")
    tipo_veiculo = models.CharField(max_length=100)
    tipo_carreta = models.CharField(max_length=100, blank=True)
    eixos_minimos = models.PositiveSmallIntegerField(null=True, blank=True)
    eixos_maximos = models.PositiveSmallIntegerField(null=True, blank=True)
    observacoes = models.CharField(max_length=300, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("produto", "tipo_veiculo", "tipo_carreta"), name="veiculo_produto_unico")]


class IndicadorFrete(models.Model):
    class Confianca(models.TextChoices):
        BAIXA = "BAIXA", "Baixa"
        MEDIA = "MEDIA", "Média"
        ALTA = "ALTA", "Alta"

    produto = models.ForeignKey(ProdutoLogistico, on_delete=models.CASCADE, related_name="indicadores_frete")
    origem_regiao = models.CharField(max_length=80, default="BRASIL")
    destino_regiao = models.CharField(max_length=80, default="BRASIL")
    faixa_distancia = models.CharField(max_length=20, choices=(("CURTA", "Curta"), ("MEDIA", "Média"), ("LONGA", "Longa"), ("GERAL", "Geral")))
    tipo_veiculo = models.CharField(max_length=100, blank=True)
    faixa_minima_tkm = models.DecimalField(max_digits=8, decimal_places=4)
    faixa_media_tkm = models.DecimalField(max_digits=8, decimal_places=4)
    faixa_maxima_tkm = models.DecimalField(max_digits=8, decimal_places=4)
    ultima_atualizacao = models.DateField()
    fonte = models.CharField(max_length=300)
    nivel_confianca = models.CharField(max_length=8, choices=Confianca.choices, default=Confianca.BAIXA)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("produto", "origem_regiao", "destino_regiao", "faixa_distancia", "tipo_veiculo"), name="indicador_frete_unico")]


class FluxoLogistico(models.Model):
    origem = models.ForeignKey(PoloLogisticoNacional, on_delete=models.CASCADE, related_name="fluxos_saida")
    destino = models.ForeignKey(PoloLogisticoNacional, on_delete=models.CASCADE, related_name="fluxos_entrada")
    produto = models.ForeignKey(ProdutoLogistico, on_delete=models.CASCADE)
    volume = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    importancia = models.PositiveSmallIntegerField(default=1)
    tipo_fluxo = models.CharField(max_length=40, default="RECORRENTE")
    fonte = models.CharField(max_length=300)
    ativo = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("origem", "destino", "produto", "tipo_fluxo"), name="fluxo_logistico_unico")]


class PracaPedagio(models.Model):
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


class EntidadeEmpresa(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)

    class Meta:
        abstract = True


class LocalLogistico(EntidadeEmpresa):
    class Tipo(models.TextChoices):
        BASE = "BASE", "Base operacional"
        POLO = "POLO", "Polo estratégico"

    nome = models.CharField(max_length=120)
    cidade = models.CharField(max_length=120)
    estado = models.CharField(max_length=2)
    tipo = models.CharField(max_length=8, choices=Tipo.choices)
    prioridade = models.PositiveSmallIntegerField(default=0)
    probabilidade_manual = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("empresa", "cidade", "estado", "tipo"), name="local_empresa_unico")]


class ParceiroFrete(EntidadeEmpresa):
    nome = models.CharField(max_length=160)
    cidade = models.CharField(max_length=120, blank=True)
    estado = models.CharField(max_length=2, blank=True)
    confiabilidade = models.DecimalField(max_digits=5, decimal_places=4, default=0)
    ativo = models.BooleanField(default=True)


class RotaEstrategica(EntidadeEmpresa):
    origem = models.ForeignKey(LocalLogistico, on_delete=models.CASCADE, related_name="rotas_origem")
    destino = models.ForeignKey(LocalLogistico, on_delete=models.CASCADE, related_name="rotas_destino")
    tipo_carga = models.CharField(max_length=80, blank=True)
    recorrente = models.BooleanField(default=True)
    ativo = models.BooleanField(default=True)

    def clean(self):
        if self.origem_id and self.origem.empresa_id != self.empresa_id:
            raise ValidationError("A origem deve pertencer à empresa da rota.")
        if self.destino_id and self.destino.empresa_id != self.empresa_id:
            raise ValidationError("O destino deve pertencer à empresa da rota.")


class PerfilEstrategia(EntidadeEmpresa):
    class Tipo(models.TextChoices):
        CONSERVADOR = "CONSERVADOR", "Conservador"
        RENTABILIDADE = "RENTABILIDADE", "Rentabilidade"
        OPERACIONAL = "OPERACIONAL", "Operacional"
        REDUCAO_VAZIO = "REDUCAO_VAZIO", "Redução de vazio"
        PERSONALIZADO = "PERSONALIZADO", "Personalizado"

    nome = models.CharField(max_length=120)
    tipo = models.CharField(max_length=24, choices=Tipo.choices, default=Tipo.PERSONALIZADO)
    pesos = models.JSONField(default=dict)
    ativo = models.BooleanField(default=True)


class ConfiguracaoLogisticaEmpresa(EntidadeEmpresa):
    class Nivel(models.TextChoices):
        GLOBAL = "GLOBAL", "Empresa"
        OPERACAO = "OPERACAO", "Operação"
        CAMINHAO = "CAMINHAO", "Caminhão"
        CARRETA = "CARRETA", "Carreta"
        DECISAO = "DECISAO", "Decisão"

    nivel = models.CharField(max_length=12, choices=Nivel.choices, default=Nivel.GLOBAL)
    operacao = models.CharField(max_length=80, blank=True)
    caminhao_id = models.PositiveIntegerField(null=True, blank=True)
    carreta_id = models.PositiveIntegerField(null=True, blank=True)
    decisao_referencia = models.CharField(max_length=80, blank=True)
    tile_provider = models.CharField(max_length=30, default="osm")
    tile_provider_url = models.URLField(blank=True)
    raio_padrao_busca_km = models.DecimalField(max_digits=8, decimal_places=2, default=150)
    km_vazio_maximo_desejado = models.DecimalField(max_digits=8, decimal_places=2, default=100)
    tempo_espera_maximo_horas = models.DecimalField(max_digits=7, decimal_places=2, default=24)
    margem_minima_desejada = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    custo_medio_hora_parada = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    custo_manutencao_por_km = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    custo_pneu_por_km = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    consumo_padrao_vazio = models.DecimalField(max_digits=6, decimal_places=2, default=2.5)
    consumo_padrao_carregado = models.DecimalField(max_digits=6, decimal_places=2, default=2)
    pesos = models.JSONField(default=dict)
    considerar_pedagio = models.BooleanField(default=True)
    considerar_comissao = models.BooleanField(default=True)
    considerar_custo_hora_parada = models.BooleanField(default=True)
    usar_recomendacoes_ia = models.BooleanField(default=False)
    quantidade_minima_registros_ia = models.PositiveIntegerField(default=100)
    ativo = models.BooleanField(default=True)
    atualizado_em = models.DateTimeField(auto_now=True)


class OportunidadeFrete(EntidadeEmpresa):
    parceiro = models.ForeignKey(ParceiroFrete, on_delete=models.PROTECT, null=True, blank=True)
    origem = models.CharField(max_length=120)
    destino = models.CharField(max_length=120)
    tipo_carga = models.CharField(max_length=80)
    tipo_veiculo = models.CharField(max_length=80, blank=True)
    capacidade_minima = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    receita = models.DecimalField(max_digits=12, decimal_places=2)
    custo_estimado = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    km_vazio = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    distancia_carregada_km = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    tempo_espera_horas = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    probabilidade_continuidade = models.DecimalField(max_digits=5, decimal_places=4, default=0)
    risco_retorno_vazio = models.DecimalField(max_digits=5, decimal_places=4, default=0)
    expira_em = models.DateTimeField(null=True, blank=True)
    telefone_contato = models.CharField(max_length=30, blank=True)
    fonte_nome = models.CharField(max_length=120, default="Cadastro manual")
    fonte_url = models.URLField(blank=True)
    verificado_em = models.DateTimeField(null=True, blank=True)
    disponibilidade_confirmada = models.BooleanField(default=False)
    ativo = models.BooleanField(default=True)

    @property
    def lucro_estimado(self):
        return self.receita - self.custo_estimado

    @property
    def valor_km_carregado(self):
        if not self.distancia_carregada_km:
            return None
        return self.receita / self.distancia_carregada_km

    @property
    def valor_km_com_vazio(self):
        distancia = (self.distancia_carregada_km or 0) + self.km_vazio
        return self.receita / distancia if distancia else None

    def clean(self):
        if self.parceiro_id and self.parceiro.empresa_id != self.empresa_id:
            raise ValidationError("O parceiro deve pertencer à empresa da oportunidade.")


class DecisaoLogistica(EntidadeEmpresa):
    perfil = models.ForeignKey(PerfilEstrategia, on_delete=models.PROTECT, null=True, blank=True)
    oportunidade_recomendada = models.ForeignKey(OportunidadeFrete, on_delete=models.PROTECT, related_name="recomendacoes")
    oportunidade_escolhida = models.ForeignKey(OportunidadeFrete, on_delete=models.PROTECT, related_name="escolhas", null=True, blank=True)
    alternativas = models.JSONField(default=list)
    explicacao = models.JSONField(default=list)
    avisos = models.JSONField(default=list)
    modo = models.CharField(max_length=16, default="REGRAS")
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    criado_em = models.DateTimeField(auto_now_add=True)
    avaliacao = models.CharField(max_length=24, blank=True)
    motivo_feedback = models.CharField(max_length=160, blank=True)
    resultado_real = models.JSONField(default=dict)


class ResultadoAprendizadoLogistico(EntidadeEmpresa):
    decisao = models.OneToOneField(DecisaoLogistica, on_delete=models.CASCADE, related_name="resultado_aprendizado")
    oportunidade = models.ForeignKey(OportunidadeFrete, on_delete=models.PROTECT)
    aceitou_sugestao = models.BooleanField(null=True, blank=True)
    features = models.JSONField(default=dict)
    lucro_previsto = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    lucro_real = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    receita_real = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    custos_reais = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    km_vazio_real = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    tempo_espera_real_horas = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    retorno_vazio_real = models.BooleanField(null=True, blank=True)
    registrado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=("empresa", "atualizado_em"))]


class ModeloLogisticoIA(EntidadeEmpresa):
    class Status(models.TextChoices):
        TREINAMENTO = "EM_TREINAMENTO", "Em treinamento"
        VALIDACAO = "EM_VALIDACAO", "Em validação"
        ATIVO = "ATIVO", "Ativo"
        REPROVADO = "REPROVADO", "Reprovado"
        SUBSTITUIDO = "SUBSTITUIDO", "Substituído"
        DESATIVADO = "DESATIVADO", "Desativado"

    tipo_modelo = models.CharField(max_length=80)
    versao = models.CharField(max_length=40)
    algoritmo = models.CharField(max_length=100)
    periodo_treinamento_inicio = models.DateTimeField(null=True, blank=True)
    periodo_treinamento_fim = models.DateTimeField(null=True, blank=True)
    quantidade_registros = models.PositiveIntegerField(default=0)
    features_utilizadas = models.JSONField(default=list)
    metricas = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TREINAMENTO)
    data_treinamento = models.DateTimeField(null=True, blank=True)
    arquivo_modelo = models.CharField(max_length=500, blank=True)
    observacoes = models.TextField(blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("empresa", "tipo_modelo", "versao"), name="modelo_versao_empresa_unico")]
