from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoriaDespesaViewSet,
    MotoristaViewSet,
    DespesaViewSet
)

router = DefaultRouter()
router.register(r'categorias', CategoriaDespesaViewSet, basename='categoria')
router.register(r'motoristas', MotoristaViewSet, basename='motorista')
router.register(r'despesas', DespesaViewSet, basename='despesa')

urlpatterns = [
    path('', include(router.urls)),
]

"""
ENDPOINTS DISPONÍVEIS:

=== CATEGORIAS ===
GET    /api/despesas/categorias/                    - Lista todas as categorias
POST   /api/despesas/categorias/                    - Cria nova categoria
GET    /api/despesas/categorias/{id}/               - Detalhes de uma categoria
PUT    /api/despesas/categorias/{id}/               - Atualiza categoria (completo)
PATCH  /api/despesas/categorias/{id}/               - Atualiza categoria (parcial)
DELETE /api/despesas/categorias/{id}/               - Remove categoria

=== MOTORISTAS ===
GET    /api/despesas/motoristas/                    - Lista todos os motoristas
POST   /api/despesas/motoristas/                    - Cria novo motorista
GET    /api/despesas/motoristas/{id}/               - Detalhes de um motorista
PUT    /api/despesas/motoristas/{id}/               - Atualiza motorista (completo)
PATCH  /api/despesas/motoristas/{id}/               - Atualiza motorista (parcial)
DELETE /api/despesas/motoristas/{id}/               - Remove motorista

Query params:
  ?ativo=true|false                                 - Filtra por status ativo
  ?caminhao=<id>                                    - Filtra por caminhão

=== DESPESAS ===
GET    /api/despesas/despesas/                      - Lista todas as despesas
POST   /api/despesas/despesas/                      - Cria nova despesa
GET    /api/despesas/despesas/{id}/                 - Detalhes de uma despesa
PUT    /api/despesas/despesas/{id}/                 - Atualiza despesa (completo)
PATCH  /api/despesas/despesas/{id}/                 - Atualiza despesa (parcial)
DELETE /api/despesas/despesas/{id}/                 - Remove despesa

POST   /api/despesas/despesas/{id}/marcar_pago/     - Marca despesa como paga
POST   /api/despesas/despesas/{id}/marcar_pendente/ - Marca despesa como pendente

GET    /api/despesas/despesas/balanco_mensal/       - Balanço mensal detalhado
GET    /api/despesas/despesas/resumo_anual/         - Resumo do ano completo
GET    /api/despesas/despesas/por_caminhao/         - Custos agrupados por caminhão
GET    /api/despesas/despesas/vencimentos_proximos/ - Despesas com vencimento próximo

Query params para listagem:
  ?caminhao=<id>                                    - Filtra por caminhão
  ?categoria=<id>                                   - Filtra por categoria
  ?tipo=OPERACIONAL|EVENTUAL                        - Filtra por tipo
  ?status=PENDENTE|PAGO                             - Filtra por status
  ?ano=<ano>                                        - Filtra por ano da competência
  ?mes=<mes>                                        - Filtra por mês da competência

==========================================================================
EXEMPLOS DE USO:
==========================================================================

# 1. CRIAR UMA DESPESA SIMPLES
POST /api/despesas/despesas/
Body: {
    "categoria_id": 1,
    "caminhao_id": 1,
    "descricao": "IPVA Janeiro 2025",
    "tipo": "OPERACIONAL",
    "valor": "1000.00",
    "competencia": "2025-01-01",
    "data_vencimento": "2025-01-15"
}

# 2. CRIAR SALÁRIO DE MOTORISTA
POST /api/despesas/despesas/
Body: {
    "categoria_id": 5,              # ID da categoria SALARIO
    "caminhao_id": 1,
    "motorista_id": 1,
    "descricao": "Salário João - Janeiro/2025",
    "tipo": "OPERACIONAL",
    "valor": "3500.00",
    "competencia": "2025-01-01",
    "data_vencimento": "2025-01-05"
}

# 3. CRIAR MANUTENÇÃO EVENTUAL
POST /api/despesas/despesas/
Body: {
    "categoria_id": 7,              # ID da categoria MANUTENCAO
    "caminhao_id": 1,
    "descricao": "Troca de pneus",
    "tipo": "EVENTUAL",
    "valor": "2500.00",
    "competencia": "2025-03-01",
    "observacoes": "Troca completa do eixo traseiro"
}

# 4. MARCAR DESPESA COMO PAGA
POST /api/despesas/despesas/42/marcar_pago/

# 5. BALANÇO MENSAL DE UM CAMINHÃO ESPECÍFICO
GET /api/despesas/despesas/balanco_mensal/?ano=2025&mes=3&caminhao=1

Retorna:
{
    "ano": 2025,
    "mes": 3,
    "caminhao_id": 1,
    "totais": {
        "total_geral": 15000.00,
        "total_pago": 8000.00,
        "total_pendente": 7000.00
    },
    "por_tipo": {
        "operacional": 12000.00,
        "eventual": 3000.00
    },
    "por_categoria": [
        {"categoria": "IPVA", "cor": "#6366F1", "total": 5000.00},
        {"categoria": "SALARIO", "cor": "#10B981", "total": 3500.00}
    ],
    "despesas": [...],
    "quantidade": 12
}

# 6. RESUMO ANUAL DE TODOS OS CAMINHÕES
GET /api/despesas/despesas/resumo_anual/?ano=2025

Retorna:
{
    "ano": 2025,
    "caminhao_id": null,
    "total_anual": 120000.00,
    "por_mes": [
        {"mes": 1, "competencia": "01/2025", "total": 10000.00},
        {"mes": 2, "competencia": "02/2025", "total": 9500.00},
        ...
    ]
}

# 7. CUSTOS POR CAMINHÃO EM MARÇO/2025
GET /api/despesas/despesas/por_caminhao/?ano=2025&mes=3

Retorna:
{
    "ano": 2025,
    "mes": 3,
    "caminhoes": [
        {
            "caminhao_id": 1,
            "nome": "Cavalo A + Carreta 1",
            "placa": "ABC-1234",
            "total": 15000.00,
            "quantidade_despesas": 12
        },
        {
            "caminhao_id": 2,
            "nome": "Cavalo B + Carreta 2",
            "placa": "DEF-5678",
            "total": 12000.00,
            "quantidade_despesas": 10
        }
    ]
}

# 8. DESPESAS COM VENCIMENTO NOS PRÓXIMOS 7 DIAS
GET /api/despesas/despesas/vencimentos_proximos/?dias=7&caminhao=1

Retorna:
{
    "dias": 7,
    "data_inicial": "2025-03-20",
    "data_final": "2025-03-27",
    "quantidade": 3,
    "despesas": [...]
}

# 9. FILTRAR DESPESAS PENDENTES DE UM CAMINHÃO
GET /api/despesas/despesas/?caminhao=1&status=PENDENTE

# 10. FILTRAR DESPESAS DE MANUTENÇÃO DO ANO
GET /api/despesas/despesas/?categoria=7&ano=2025

==========================================================================
WORKFLOW TÍPICO:
==========================================================================

1. INÍCIO DO MÊS - CRIAR DESPESAS OPERACIONAIS:
   - IPVA (se aplicável)
   - Seguro (se aplicável)
   - Rastreador
   - Salários dos motoristas
   - Licenciamento (se aplicável)

2. DURANTE O MÊS - REGISTRAR DESPESAS EVENTUAIS:
   - Manutenções
   - Multas
   - Guinchos
   - Franquias de seguro
   - Outros

3. PAGAMENTO:
   - Marcar cada despesa como paga conforme for quitando

4. FIM DO MÊS - ANÁLISE:
   - Ver balanço mensal completo
   - Comparar custos por caminhão
   - Analisar categorias que mais custaram

5. PLANEJAMENTO:
   - Ver vencimentos próximos
   - Analisar resumo anual
   - Projetar custos futuros
"""