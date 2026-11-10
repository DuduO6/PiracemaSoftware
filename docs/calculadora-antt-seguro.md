# Calculadora ANTT e seguro comercial

## Escopo

A funcionalidade apenas calcula e apresenta valores para uso manual. Ela não emite CT-e, não preenche emissores externos e não integra com seguradoras ou apólices.

O XML de NF-e/CT-e é lido somente para obter município/UF de origem e destino, valor da carga e peso. Os dados importados são compartilhados localmente entre a calculadora ANTT e a página de seguro.

## Regras financeiras

Os cálculos críticos são executados no backend com `Decimal` e arredondamento `ROUND_HALF_UP`:

```text
seguro_final = max(piso_comercial, valor_original_planilha * multiplicador + acrescimo_fixo)
valor_final = piso_antt + seguro_final + margem_adicional + pedagio + outras_despesas
```

Padrões iniciais:

- multiplicador do seguro: `2`;
- acréscimo fixo: `R$ 6,00`;
- piso comercial: `R$ 30,00`;
- margem adicional: `R$ 200,00`;
- distribuição ilustrativa: `50%` para RCTR-C e `50%` para RC-DC;
- precisão dos percentuais: `6` casas decimais.

A distribuição 50/50 é uma sugestão matemática e não representa taxas oficiais ou contratadas. Taxas reais podem ser registradas apenas como referência. Percentuais manuais também são aceitos.

Após arredondar cada percentual à precisão configurada, o backend recalcula os valores monetários efetivos, compara a soma ao seguro esperado e retorna a diferença. A interface só afirma reprodução exata quando a diferença monetária é zero.

## Endpoints

- `POST /api/seguro-cargas/importar-xml/`: importa NF-e ou CT-e.
- `POST /api/seguro-cargas/calcular/`: consulta a matriz existente e calcula seguro, percentuais e total comercial.
- `POST /api/fretes/calcular/`: mantém o cálculo ANTT e, quando recebe `valor_carga`, inclui o mesmo cálculo de seguro e o valor final sugerido.

## Validação automatizada

Em 9 de novembro de 2026 foram executados:

```text
USE_SQLITE=True DEBUG=True ../venv/bin/python manage.py test
34 testes executados — OK

npm run build
Build de produção concluído
```

O build preserva três avisos ESLint preexistentes em `Despesas.jsx`, `MotoristaDetalhes.jsx` e `Register.jsx`, sem relação com esta funcionalidade.
