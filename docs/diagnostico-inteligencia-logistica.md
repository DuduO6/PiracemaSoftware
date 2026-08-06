# Diagnóstico técnico — Inteligência Logística

## Resumo executivo

O sistema atual registra viagens, caminhões, carretas, motoristas e algumas parcelas financeiras, mas os registros legados são vinculados diretamente ao usuário e não a uma organização. Isso permite análises descritivas básicas, porém ainda não sustenta previsões contextuais confiáveis. A primeira entrega deve operar com regras, pesos configuráveis e feedback, enquanto a coleta é ampliada.

## Dados disponíveis

- Viagem: data, origem, destino, cliente, motorista, peso, valor por tonelada, valor bruto/líquido e presença de CT-e.
- Caminhão/carreta: identificação e parte dos custos fixos; o vínculo atual é com o usuário.
- Motorista, vales, despesas e acertos.
- Avaliação pontual de lucro de viagem, sem persistir todo o contexto e o resultado previsto.

Esses campos permitem rankings de rotas, frequência origem–destino, receita por rota/período, sazonalidade simples e grafos descritivos por tenant após a migração dos registros legados.

## Dados ausentes ou insuficientes

- quilômetros vazios previstos e realizados;
- horário de chegada, início/fim da espera e carregamento;
- oportunidade considerada, recusada, aceita, alterada ou cancelada;
- tipo de carga normalizado, veículo/carreta usados, eixos e capacidade no evento;
- parceiro ofertante, contatos, conversão e disponibilidade observada;
- pedágios, combustível, manutenção, pneus, comissão e demais custos reais por viagem;
- compromissos, jornada, restrições e motivo da decisão;
- resultado de busca por carga dentro de uma janela definida;
- localização/contexto conhecido no instante da recomendação;
- safra, região e recência da observação;
- encadeamento explícito das viagens em ciclos.

Sem esses dados não há alvo confiável para carga encontrada, espera, lucro real ou retorno vazio.

## Arquitetura entregue

O app `inteligencia_logistica` introduz empresa, membros e papéis; bases/polos; parceiros e rotas; configuração hierárquica; perfis de pesos; oportunidades; decisões/feedback; e registro versionado de modelos. A API exige `X-Empresa-ID`, limita querysets ao tenant e valida referências relacionadas. O recomendador determinístico filtra regras obrigatórias antes da pontuação e continua funcional sem IA.

A configuração da Piracema é criada como dado de tenant pelo comando:

```bash
python manage.py configurar_primeiro_cliente
```

Ela não é constante global. Associar os usuários autorizados à empresa deve ser uma ação administrativa explícita.

## Análises e modelos recomendados

1. Instrumentação e análises descritivas: iniciar agora. Medir frequência, lucro, vazio, espera e conversão por rota/parceiro/período.
2. Regras adaptativas: após resultados consistentes, combinar estimativa manual e taxa histórica com suavização bayesiana e decaimento temporal.
3. Classificação de carga encontrada: regressão logística como referência; avaliar árvores/boosting somente com diversidade suficiente.
4. Regressão de espera e lucro: referência por mediana de grupo, depois modelos de árvores. Para espera com censura, avaliar análise de sobrevivência.
5. Risco de retorno vazio: classificação calibrada e comparada à frequência histórica.
6. Grafos/ciclos: agregação dirigida de viagens e busca limitada; não requer ML na primeira fase.

Referências iniciais por tenant: abaixo de 30 decisões, regras; 30–100, estatística exploratória; 100–300, modelos simples com confiança limitada; acima de 300, avaliar modelos supervisionados. A ativação depende também de cobertura dos alvos, diversidade e qualidade, não apenas da contagem.

## Avaliação e prevenção de vazamento

Usar divisão temporal: treino antigo, validação posterior e teste mais recente. Features devem ser reconstruídas conforme eram conhecidas na data da decisão. Não usar resultado final, próxima viagem real ou agregados calculados com eventos futuros.

Classificação: precision, recall, F1, ROC-AUC, PR-AUC, calibração e matriz de confusão. Regressão: MAE, RMSE, erro mediano e cortes por região/carga. Negócio: lucro líquido, quilômetros vazios, espera, aceitação e diferença previsto–real. Um modelo só deve ser ativado se superar a pontuação determinística e referências simples em período posterior.

## Riscos e plano incremental

Os principais riscos são dados legados sem empresa, seleção enviesada (somente viagens aceitas), alvos ausentes, mudanças de mercado, pouca diversidade e explicações aparentes sem evidência. Não compartilhar dados entre tenants; qualquer estatística agregada futura exige consentimento e anonimização.

Plano: (1) associar dados legados a empresas com migração auditada; (2) coletar contexto e resultados; (3) publicar painel descritivo; (4) calibrar probabilidades históricas; (5) treinar modelos manualmente fora de HTTP; (6) validar temporalmente e registrar versões; (7) ativar gradualmente com fallback para regras; (8) monitorar degradação previsto–real.
