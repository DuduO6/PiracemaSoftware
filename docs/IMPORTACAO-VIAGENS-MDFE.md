# Importação de viagens a partir de MDF-e

## Fluxo

Na página **Viagens**, a ação **Importar dos MDF-e** consulta os manifestos não encerrados usando o serviço `MDFeConsNaoEnc` existente. A consulta atualiza o cache normal do módulo MDF-e e prepara uma prévia a partir do XML criptografado já armazenado.

A preparação não cria viagens. O usuário precisa selecionar cada MDF-e, revisar motorista, trecho, cliente, peso, valor por tonelada, CT-e, aplicação do desconto e situação de pagamento e confirmar explicitamente o salvamento. A empresa é obtida automaticamente do único vínculo ativo do usuário e não precisa ser selecionada no modal.

XML classificado como `INFORMATIVO`, divergência de motorista, possível duplicidade histórica e diferença entre o contrato declarado e o valor líquido exigem confirmações específicas.

## Endpoints

### `POST /api/viagens/consultar-mdfe-abertos/`

Requer autenticação, cabeçalho `X-Empresa-ID` e vínculo ativo com a empresa. Perfis `LEITURA` podem consultar, mas não confirmar a importação. Reutiliza a consulta de MDF-e não encerrados e o download/cache já implementado. Retorna somente os campos necessários à revisão; não retorna XML, CPF completo, certificado ou conteúdo criptografado.

### `POST /api/viagens/importar-mdfe-confirmados/`

Recebe `registros`, reabre os MDF-e da empresa sob bloqueio transacional, descriptografa e valida novamente cada XML, confirma que os CT-e enviados pertencem ao documento e valida o motorista no escopo do usuário.

O lote é atômico: todas as viagens e vínculos fiscais são gravados ou nenhuma alteração é persistida. Cada viagem é criada pelo `ViagemSerializer` e pelo mesmo serviço de persistência usado no cadastro normal.

## Persistência

A migration `viagens/0003_importacaomdfeviagem.py` cria apenas `ImportacaoMdfeViagem`, uma tabela auxiliar de rastreabilidade. Os dados operacionais e financeiros continuam exclusivamente em `Viagem`.

As restrições impedem reutilizar, na mesma empresa:

- uma chave de MDF-e já importada;
- uma chave de CT-e já importada.

Quando não há CT-e, a chave é armazenada como `NULL`; isso permite vários registros sem CT-e e mantém a restrição de unicidade compatível com MySQL.

Se a viagem for excluída pelo fluxo atual, a rastreabilidade fiscal permanece com `viagem = NULL`, impedindo reimportação acidental.

## Regras financeiras e acertos

O backend continua calculando peso × valor por tonelada pelo modelo `Viagem`. Quando existe CT-e, a checkbox `descontar_cte` define se os 10% serão aplicados. Viagens existentes com CT-e preservam o desconto habilitado; viagens sem CT-e ficam com a opção desabilitada. `vContrato` serve somente para sugerir o valor por tonelada e comparar o contrato com o valor líquido; `vCarga` não é usado como frete.

O nome em `infPag/xNome` é usado como sugestão de cliente/tomador. CPF ou CNPJ do grupo de pagamento não é enviado integralmente ao frontend.

Nenhuma alteração foi feita nos modelos, filtros ou na geração de acertos. Uma viagem importada participa do acerto pelo mesmo queryset e é copiada para `ItemAcerto` da mesma forma que qualquer viagem manual.

## Validação local

```bash
cd backend
PYTHONDONTWRITEBYTECODE=1 USE_SQLITE=True ../venv/bin/python manage.py test viagens mdfe acertos

cd ../frontend
npm run build
```

Os testes usam XMLs sintéticos e mocks para as integrações externas.

## Implantação segura

1. Fazer backup e validar a migration em homologação.
2. Configurar a mesma `MDFE_ENCRYPTION_KEY` usada para os XMLs armazenados.
3. Executar as migrations `viagens.0003_importacaomdfeviagem` e `viagens.0004_viagem_descontar_cte` na janela aprovada.
4. Publicar backend e frontend da mesma versão.
5. Testar inicialmente com uma empresa de homologação e um MDF-e sintético/controlado.
6. Verificar permissões `ADMIN`/`OPERADOR`, importação, listagem da viagem e geração de acerto.

Não é necessário reter XML após encerramento: o vínculo fiscal e as chaves já persistidas permanecem na tabela auxiliar.

## Limitações deliberadas

- O cliente/tomador nunca é inferido do pagador do MDF-e; precisa ser informado.
- Múltiplos CT-e exigem seleção manual e não provocam rateio automático.
- Unidade de peso ausente ou desconhecida exige preenchimento manual.
- O sistema não consulta distribuição DF-e, não emite CT-e e não adiciona scraping.
- Como o modelo atual `Viagem` é vinculado ao usuário, o motorista selecionado precisa pertencer ao usuário que executa a importação, além de esse usuário pertencer à empresa MDF-e escolhida.
