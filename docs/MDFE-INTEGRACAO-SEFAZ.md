# Integração MDF-e com a SEFAZ

## Visão geral

O módulo permite consultar MDF-e não encerrados e registrar o evento oficial `110112 — Encerramento` diretamente na SEFAZ Virtual Rio Grande do Sul (SVRS). O frontend nunca acessa a SEFAZ nem recebe o certificado, sua senha ou sua chave privada.

A implementação usa os modelos compartilhados `Empresa` e `MembroEmpresa`, mantidos internamente para isolamento por transportadora:

- `ADMIN`: consulta, encerra e configura os dados fiscais/certificado;
- `OPERADOR`: consulta e encerra;
- `LEITURA`: somente consulta registros locais;
- usuário sem vínculo ativo: sem acesso.

Cada chamada exige JWT e o cabeçalho `X-Empresa-ID`.

## Referências fiscais verificadas

A implementação foi confrontada em 10/11/2026 com as fontes oficiais:

- [Portal Nacional MDF-e — documentos, MOC e schemas](https://dfe-portal.svrs.rs.gov.br/mdfe/Documentos)
- [SEFAZ-MG — relação oficial dos Web Services MDF-e](https://portalsped.fazenda.mg.gov.br/spedmg/mdfe/Web-Services/)
- MOC MDF-e 3.00b — Visão Geral e Anexo I;
- pacote oficial `PL_MDFe_300b_NT012025_1.04.zip`, cujo diretório interno disponibilizado pelo portal é `PL_MDFe_300b_NT012025_1.05`;
- schemas 3.00 de consulta, situação, evento, encerramento e XMLDSig incluídos em `backend/mdfe/schemas/`;
- [AC Raiz ICP-Brasil v10 — ITI](https://www.gov.br/iti/pt-br/assuntos/repositorio/repositorio-ac-raiz).

Os endereços confirmados são:

| Serviço | Homologação | Produção |
|---|---|---|
| `MDFeConsNaoEnc` | `https://mdfe-homologacao.svrs.rs.gov.br/ws/MDFeConsNaoEnc/MDFeConsNaoEnc.asmx` | `https://mdfe.svrs.rs.gov.br/ws/MDFeConsNaoEnc/MDFeConsNaoEnc.asmx` |
| `MDFeConsulta` | `https://mdfe-homologacao.svrs.rs.gov.br/ws/MDFeConsulta/MDFeConsulta.asmx` | `https://mdfe.svrs.rs.gov.br/ws/MDFeConsulta/MDFeConsulta.asmx` |
| `MDFeRecepcaoEvento` | `https://mdfe-homologacao.svrs.rs.gov.br/ws/MDFeRecepcaoEvento/MDFeRecepcaoEvento.asmx` | `https://mdfe.svrs.rs.gov.br/ws/MDFeRecepcaoEvento/MDFeRecepcaoEvento.asmx` |

O transporte é SOAP 1.2 `Document/Literal`, TLS 1.2 ou superior com autenticação mútua. O XML do evento é assinado no `infEvento` com XMLDSig enveloped, C14N inclusivo, RSA-SHA1, digest SHA-1 e apenas o certificado final em `X509Certificate`, conforme o MOC vigente. SHA-1 é usado exclusivamente porque o leiaute fiscal oficial 3.00 ainda o exige para XMLDSig.

## Arquitetura

### Backend

O app `mdfe` separa:

- `models.py`: configuração fiscal, manifestos, consultas e operações de encerramento;
- `serializers.py` e `views.py`: API REST, validação de entrada e autorização;
- `services/certificate_service.py`: PKCS#12, validade, CNPJ ICP-Brasil, criptografia e arquivos TLS temporários;
- `services/xml_service.py`: XML 3.00, XSD, SOAP 1.2 e XMLDSig;
- `services/sefaz_client.py`: mTLS, endpoints, timeouts e SOAP Fault;
- `services/consulta_service.py`: `MDFeConsNaoEnc` e `MDFeConsulta`;
- `services/portal_download_service.py`: download autenticado do `mdfeProc` no Portal Nacional;
- `services/xml_import_service.py`: validação, extração e cache criptografado do XML;
- `services/encerramento_service.py`: pré-consulta, evento 110112, idempotência, concorrência e reconciliação;
- `schemas/`: subconjunto oficial necessário à validação local;
- `certs/icp-brasil-v10.pem`: confiança pública da AC Raiz usada atualmente pelo endpoint SVRS.

### Frontend

A rota `#/manifestos-mdfe` oferece:

- atualização fiscal manual e explícita, evitando consultas involuntárias ao Portal;
- cards de resumo (o total encerrado significa apenas o histórico desta aplicação);
- pesquisa, filtro, paginação e histórico;
- indicação explícita de dados desatualizados;
- download automático e cache do XML processado para identificar condutores e destinos;
- importação manual de XML como contingência;
- modal de encerramento sem preenchimento automático da data;
- seleção de município pela base IBGE local;
- confirmação obrigatória da conclusão da viagem;
- resultado oficial, protocolo copiável e consulta de operação inconclusiva;
- configuração fiscal disponível apenas ao papel `ADMIN`.

## Persistência e migrations

As migrations do app criam e evoluem:

- `ConfiguracaoFiscal`: uma por empresa;
- `Manifesto`: único por empresa e chave;
- `ConsultaManifestos`: auditoria de todas as tentativas de atualização;
- `OperacaoEncerramento`: auditoria do usuário, local, data, evento, retorno e protocolo.
- cache criptografado do XML, situação da obtenção, destinos e snapshot fiscal de encerramento.

Aplicar com:

```bash
cd backend
../venv/bin/python manage.py migrate
```

Não há alteração destrutiva nas tabelas de viagens, motoristas ou veículos.

## Segurança do certificado A1

1. Gere uma chave Fernet exclusiva para o ambiente:

   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

2. Salve-a no gerenciador de segredos da infraestrutura como `MDFE_ENCRYPTION_KEY`. Não a versione. A mesma chave protege o PKCS#12, a senha e os XMLs em cache.
3. Acesse **Manifestos — MDF-e > Configuração fiscal** com um usuário `ADMIN`.
4. Informe razão social, CNPJ, UF, homologação, arquivo `.pfx`/`.p12` e senha.
5. O backend valida PKCS#12, período, uso para assinatura/autenticação cliente e o CNPJ no `otherName` OID `2.16.76.1.3.3`.
6. O certificado e a senha são criptografados separadamente antes de persistir. A API retorna somente metadados (validade, fingerprint e CNPJ).
7. Durante a chamada, chave e certificado são materializados em diretório temporário com permissões `0700/0600` e removidos ao final.

Rotação: envie o novo arquivo e a nova senha na mesma tela. Nunca altere apenas a senha sem reenviar o PKCS#12. Faça backup seguro de `MDFE_ENCRYPTION_KEY`; sem ela, os registros criptografados não podem ser recuperados.

O XML assinado fica cifrado com Fernet no banco. Ele contém apenas o certificado público exigido pelo XMLDSig, nunca a chave privada ou a senha.

## Variáveis de ambiente

| Variável | Obrigatória | Padrão | Uso |
|---|---:|---|---|
| `MDFE_ENCRYPTION_KEY` | sim | vazio | criptografia Fernet do A1 e senha |
| `MDFE_ENABLE_PRODUCTION` | para produção | `False` | trava de servidor para produção |
| `MDFE_CONNECT_TIMEOUT_SECONDS` | não | `15` | timeout de conexão |
| `MDFE_READ_TIMEOUT_SECONDS` | não | `45` | timeout de resposta |
| `MDFE_CA_BUNDLE` | não | raiz v10 incluída | arquivo PEM de confiança ICP-Brasil |
| `MDFE_PORTAL_CA_BUNDLE` | não | cadeia pública do sistema | CA pública/corporativa usada no domínio web do Portal |
| `MDFE_ALLOW_INFORMATIONAL_PORTAL_XML` | não | `False` | aceita XML não verificável do Portal somente para visualização de motorista/destino |
| `MDFE_ALLOW_UNVERIFIED_PORTAL_XML` | não | `False` | exceção diagnóstica; só funciona com `DEBUG=True` |
| `MDFE_MUNICIPALITIES_FILE` | não | `backend/mdfe/data/municipiosBrasil.json` | base IBGE local usada na validação |

Nunca use `verify=False`. Quando a SVRS trocar a cadeia do servidor, atualize o bundle a partir do repositório oficial do ITI e valide fingerprint/issuer antes da implantação.

## API REST

| Método | Endpoint | Função |
|---|---|---|
| `GET` | `/api/mdfe/pendentes/` | lista paginada, resumo e estado da última consulta |
| `GET/POST` | `/api/mdfe/empresas/` | lista empresas do usuário ou cria seu vínculo inicial |
| `POST` | `/api/mdfe/atualizar/` | consulta `MDFeConsNaoEnc`, tenta obter os XMLs ausentes e extrai dados |
| `POST` | `/api/mdfe/importar-xml/` | valida XML processado e vincula condutores cadastrados pelo CPF |
| `GET` | `/api/mdfe/{chave}/` | detalhe local |
| `POST` | `/api/mdfe/{chave}/encerrar/` | pré-consulta e transmissão do 110112 |
| `GET` | `/api/mdfe/historico/` | encerrados confirmados pelo sistema |
| `GET` | `/api/mdfe/operacoes/{uuid}/` | auditoria segura da operação |
| `POST` | `/api/mdfe/operacoes/{uuid}/confirmar/` | consulta situação oficial de operação inconclusiva |
| `GET/PUT` | `/api/mdfe/configuracao/` | configuração administrativa e rotação do A1 |

O endpoint de encerramento aceita `Idempotency-Key`. Sem o cabeçalho, o backend deriva uma chave estável do MDF-e/local/data. Cliques ou requisições repetidas com a mesma chave retornam a operação existente.

## Fluxo de consulta

1. Carrega e valida o certificado da empresa.
2. Monta `consMDFeNaoEnc` 3.00 (`xServ=CONSULTAR NÃO ENCERRADOS`).
3. Valida o XML de entrada com XSD.
4. Envia via SOAP 1.2/mTLS.
5. Valida e interpreta a resposta oficial.
6. `cStat=111`: sincroniza chaves/protocolos; `cStat=112`: consulta válida sem itens.
7. Para cada chave aberta, reutiliza o XML cifrado existente ou tenta o download autenticado no Portal Nacional.
8. Valida e interpreta o `mdfeProc`, vincula o motorista pelo CPF e grava todos os municípios de descarga.
9. Só então encerra a requisição e informa quantos XMLs foram baixados, reutilizados ou falharam.
10. Qualquer outro código fiscal é rejeição, não sucesso. Falha de um XML é registrada no manifesto e não descarta a lista válida devolvida pela SEFAZ.

O serviço fornece chave e protocolo; o número é extraído da própria chave fiscal. Data exata de emissão e dados da viagem não são inventados.

## XML, motorista e destino

`MDFeConsNaoEnc` não retorna condutores nem municípios de descarga. Ao atualizar, o backend tenta obter cada `mdfeProc` ausente com o mesmo A1, sem criar arquivo permanente no servidor. O documento integral é cifrado antes de entrar no banco; uma consulta posterior da mesma chave reutiliza esse cache e não repete o download.

Como contingência, um administrador ou operador ainda pode usar **Importar XML** e selecionar até 20 arquivos processados, com no máximo 5 MB cada.

Antes de persistir qualquer dado, o backend valida o schema oficial, a chave de acesso, o CNPJ-base, o ambiente, o protocolo previamente consultado, `cStat=100`, o certificado público do emitente, o digest confirmado pelo protocolo e a XMLDSig integral. DTD e entidades externas não são permitidos. Se a assinatura do conteúdo devolvido pelo Portal não puder ser reproduzida localmente, o XML é rejeitado e não entra no cache.

Cada CPF do grupo rodoviário é comparado com os motoristas pertencentes aos usuários ativos da empresa. Quando há correspondência, o vínculo é automático. Quando não há, o nome informado no XML permanece visível como **Somente no XML**, sem criar motorista automaticamente. A API mascara o CPF e a interface mostra também os municípios de descarga e a UF final.

## Fluxo de encerramento

1. Bloqueia o manifesto no banco e impede operação simultânea.
2. Valida empresa, CNPJ-base, município IBGE, UF, data e confirmação.
3. Executa `MDFeConsulta` antes da transmissão.
4. Confirma estado autorizado (`cStat=100`) e protocolo.
5. Gera, valida e assina o XML `110112`.
6. Persiste o XML antes da transmissão.
7. Envia ao `MDFeRecepcaoEvento`.
8. Somente `cStat=135` com `nProt` marca o evento como homologado.
9. `cStat=132` em consulta posterior também confirma encerramento, desde que o protocolo oficial do evento esteja presente.
10. Rejeições nunca mudam o manifesto para encerrado.
11. Após confirmação oficial, cria um snapshot com chave, protocolos, datas, condutores e destinos; em seguida remove somente o blob XML cifrado. Condutores, destinos, SHA-256 e snapshot permanecem para o histórico.

Em timeout de transmissão, o estado é **Situação a confirmar**. Nova transmissão é bloqueada. O usuário deve usar **Consultar situação oficial**; o sistema consulta o documento e só conclui com evidência oficial suficiente. Um timeout não é tratado como falha fiscal nem como sucesso.

## Tratamento de erros

Há categorias explícitas para configuração ausente, certificado inválido/expirado/incompatível, uso de chave inadequado, TLS, timeout, indisponibilidade, SOAP Fault, XML inválido, schema, resposta inesperada, rejeição, protocolo divergente, documento cancelado/encerrado e persistência.

As respostas ao frontend não incluem exceções internas, senha, PKCS#12 ou chave privada. Os códigos e descrições fiscais apresentados são os retornados pela SEFAZ; nenhum protocolo é gerado localmente.

## Execução local

Backend:

```bash
cd backend
cp .env.local.example .env.local
# defina MDFE_ENCRYPTION_KEY em .env.local
../venv/bin/pip install -r requirements.txt
../venv/bin/python manage.py migrate
../venv/bin/python manage.py runserver
```

Frontend:

```bash
cd frontend
npm install
npm start
```

## Testes

```bash
cd backend
USE_SQLITE=True ../venv/bin/python manage.py test mdfe.tests -v 2

cd ../frontend
npm run build
```

A suíte cobre CNPJ, validade/vínculo do certificado, zero/múltiplos manifestos, download e cache, extração de motorista/destino, XML inválido, comunicação, documento já encerrado, descarte do blob, snapshot, rejeição, homologação, timeout, duplicidade, concorrência, persistência, acesso, ausência de vazamento e assinatura/XSD.

Os testes usam PKCS#12 e respostas XML gerados apenas para teste. Eles não inventam protocolo em produção nem substituem homologação real.

## Homologação

1. Mantenha `MDFE_ENABLE_PRODUCTION=False`.
2. Cadastre um A1 válido e ambiente **Homologação**.
3. Confirme que o contribuinte está credenciado como emissor e possui MDF-e de homologação compatível.
4. Faça a consulta e confira `cStat`, motivo e chaves retornadas.
5. Escolha apenas um documento de homologação preparado para o ensaio.
6. Confirme município/data reais do cenário de teste.
7. Compare XML, protocolo e consulta posterior com o portal oficial.
8. Registre evidências e valide com a área fiscal antes de liberar produção.

## Liberação para produção

Produção requer duas travas simultâneas:

1. segredo do servidor `MDFE_ENABLE_PRODUCTION=True`;
2. seleção de **Produção** e confirmação explícita por administrador na tela.

Antes disso, valide backup, monitoração, cadeia ICP-Brasil, relógio do servidor, política de acesso, rotação do A1 e plano de resposta a operações **Situação a confirmar**. Não use documentos reais de produção em homologação.

## Limitações e manutenção

- O download autenticado foi ensaiado em produção com um A1 real em 10/11/2026, sem transmissão de evento fiscal.
- O Web Service oficial `MDFeDistribuicaoDFe` não fornece documentos emitidos pela própria empresa (NT 2015.002). Por isso, para o emitente, a recuperação usa a página autenticada de download do Portal Nacional, que não é um contrato de Web Service e pode mudar.
- O Portal aplica bloqueio temporário por excesso de consultas. O backend reconhece esse retorno, interrompe novas tentativas no mesmo ciclo, mantém os registros pendentes e reutiliza tudo que já estiver em cache. Não tente contornar o bloqueio; aguarde e atualize novamente ou use a importação manual.
- No ensaio real, o HTML do Portal devolveu um XML cuja forma reserializada não passou na verificação integral da XMLDSig. O padrão continua estrito. Quando houver autorização explícita de política, `MDFE_ALLOW_INFORMATIONAL_PORTAL_XML=True` permite armazená-lo cifrado e extrair motorista/destino, classificando-o como `INFORMATIVO`. Chave, CNPJ-base, ambiente, protocolo, certificado público e digest informado continuam sendo conferidos. Esses dados aparecem com aviso na interface, não preenchem o município e não são aceitos pela API de encerramento.
- Para testes locais autorizados, `MDFE_ALLOW_UNVERIFIED_PORTAL_XML=True` permite aceitar exclusivamente respostas obtidas por HTTPS/mTLS no domínio oficial. A chave, CNPJ-base, ambiente, protocolo, certificado público e digest informado continuam sendo conferidos; `xml_assinatura_conteudo_validada=false` identifica o registro. A opção é ignorada quando `DEBUG=False`.
- `MDFeConsNaoEnc` não fornece todos os dados da viagem. O módulo não os infere.
- A base de municípios é o arquivo local existente no projeto; atualize-o quando o IBGE alterar códigos.
- Revise MOC, notas técnicas, schemas e cadeia ICP-Brasil antes de cada liberação fiscal. Mudanças oficiais devem ser incorporadas e testadas antes da ativação.
