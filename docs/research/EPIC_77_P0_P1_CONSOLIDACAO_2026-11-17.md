# EPIC #77 — Evidências P0/A-B-C e P1 (congelamento científico formalizado)

**Estado:** FROZEN_SCIENTIFIC_SYNTHETIC_EVIDENCE (decisão explícita do responsável em 17/11/2026). Registro derivado dos quatro JSONs enviados pelo pesquisador, comparados bit a bit com os hashes da listagem local. Não modifica treinamento, relatórios, CODE ou N4.

**Dataset:** GENESIS `SYNTHETIC`, SHA-256 declarado do `manifest.json`: `0e61e8e65efa02d53bd40f13587c61b771f6667f392cc87b9733c59fcee8f4c6`. Os quatro arquivos apontam para esse mesmo manifesto; seu conteúdo completo (artefatos Parquet e catálogo) não foi revalidado aqui.

| Relatório local | SHA-256 |
|---|---|
| protocolo_A.json | `4e226f97f8bdd1c62e2ff15cdd715eb63a52a89a0e3833fba578d709d427a21a` |
| protocolo_B.json | `6c9417adb5241e15cfe00e867b031d15276abe7d16cf4a809d1edf286843733d` |
| protocolo_C.json | `78bed26bc0fc209fbaa4d662d1880c3b6d6b463c5e08f0aa4779bdaf705efd08` |
| robustez_P1_v1.json | `db2fe6d7ab6b920cd69489cb7dac5ed0722083701b8286dbe991476c7c3ec8c3` |

## Macro-F1 (N1 / N2 / N3)

| Protocolo | Regressão Logística | Random Forest |
|---|---|---|
| P0/A (GroupKFold por estudante) | 0,7554 / 0,8249 / 0,8914 | 0,7490 / 0,8214 / 0,8986 |
| P0/B (temporal 2026, mesma coorte) | 0,7625 / 0,8517 / 0,8914 | 0,7700 / 0,8263 / 0,9041 |
| P1 (holdout agrupado + seleção interna aninhada) | 0,7258 / 0,7748 / 0,8490 | 0,7196 / 0,7561 / 0,8700 |

P0/C: `not_identifiable` nos três cortes (`no_unseen_future_students`). Não apresentar como pontuação zero nem alegar generalização para nova coorte.

As médias agregadas foram conferidas contra os valores por fold/seed disponíveis no JSON. P0/A, P0/B e P1 usam partições com semânticas distintas; **não** afirmar superioridade estatística ou ganho causado pela regularização com base nessa tabela.

## Auditoria de execução relatada

- Testes selecionados: **17 passed, 32 warnings**; a mensagem reportada é `Skipping features without any observed values: [5 6 7 8]` em alguns fixtures de `test_mapa_protocol_runner.py`. A origem é a imputação de históricos ausentes; risco residual de contrato de 11 colunas deve ser acompanhado, sem alteração retroativa dos resultados.
- Ambiente informado: Python 3.13.3, NumPy 2.4.4, scikit-learn 1.8.0.
- O SHA `8cdc019e36d54c981cfc5344f5a5851d8fabcfc2` descreve a `develop` **na auditoria**, não prova o commit exato da execução P0/P1. A árvore local tinha modificações não relacionadas.
- P0/B usa treino 2020–2024 e teste em 2026, 40 alunos em ambas as partições, com sobreposição integral de identificadores. Não é protocolo C.
- P1: o gap de Macro-F1 treino–teste da Random Forest (0,1947 / 0,1366 / 0,0925) excede o da Logística (0,0683 / 0,0781 / 0,0559). É indicador descritivo, não diagnóstico causal conclusivo.

## Auditoria de integridade e proveniência final

- O usuário executou `read_verified_v2()` em `D:\EPA-Experimentos\genesis-epic77-v2`, recebendo `STATUS: PASS`: cinco SHA-256 de Parquets, contagens (40, 42, 280, 324, 8.640) e validação estrutural aprovados. Essa evidência é um resultado de execução local relatado; não equivale a revalidação independente na máquina remota.
- O SHA-256 de `examples/atlas.demo.json` foi confirmado localmente: `22457cc65857d43a33726e06380bc58dfb64b6e802b89c393c43cbf03bfa0ab1`.
- GitHub: o avaliador P0/A/B/C entrou na `develop` em `69ae730af076110708ea18aa5c3df5aae94c27f3` (PR #82). O P1 entrou em `3257208d6034679ff57151f4117c3a745f78c038` (PR #83).
- Reflog local: atualização para P0 às 02:08:35 -03:00 e para P1 às 02:40:50 -03:00 em 17/11/2026; documentação posterior `8cdc019` às 03:12:34. **O reflog não registra o commit exato em cada execução Python.** São candidatos de execução, não proveniência original definitivamente comprovada.
- A avaliação por classe P0/A e P0/B reproduziu os scores originais. O P0/C segue `not_identifiable`; o P1 não contém recall por classe. O ambiente Python/scikit-learn informado foi consultado na auditoria posterior, não necessariamente na execução inicial.

## Condição para congelamento

**Pacote congelado como evidência científica sintética de escopo delimitado**, não para afirmar validade educacional externa, certificação P2 ou reprodução integral byte a byte do ambiente de execução histórico. A decisão de freeze deve registrar explicitamente que a revisão exata original é desconhecida, preservar os seis relatórios íntegros fora do Git e impedir alterações retroativas nos resultados. Se for requerida prova da revisão exata, executar replicação nova em checkout limpo e commit fixado com relatório separado.


O manifesto estruturado está em `docs/research/EPIC_77_EVIDENCE_MANIFEST_v1.json`. A EPIC operacional/P2 não está encerrada e nenhuma evidência de alunos reais integra este pacote.

## Fechamento da auditoria por classe — evidências suplementares

| Relatório privado | SHA-256 | Reprodução |
|---|---|---|
| `auditoria_classes_A.json` | `fec371cabdb531c0f3c74ea8eefea5ceba403212c6a75f9bdd8fab4c93e69531` | 27 valores de Macro-F1 por modelo/fold iguais ao P0/A |
| `auditoria_classes_B.json` | `73c69b8958ebed73117490fbb1587e02ecbaa012930cec0e46a7f6a7a8b3d066` | hashes dos splits, acurácia, Macro-F1 e contagens iguais ao P0/B |

### Recall `failed` (Reprovação)

| Protocolo | Modelo | N1 | N2 | N3 |
|---|---|---|---|---|
| P0/A agrupado (172 por corte) | LR | 87/172 (50,58%) | 113/172 (65,70%) | 134/172 (77,91%) |
| P0/A agrupado (172 por corte) | RF | 91/172 (52,91%) | 111/172 (64,53%) | 141/172 (81,98%) |
| P0/B temporal (45 por corte) | LR | 28/45 (62,22%) | 34/45 (75,56%) | 36/45 (80,00%) |
| P0/B temporal (45 por corte) | RF | 28/45 (62,22%) | 31/45 (68,89%) | 37/45 (82,22%) |

Os 45 registros de reprovação do protocolo B em 2026 são registros disciplina/ano, não estudantes independentes. Nesse teste sintético, os casos de reprovação não identificados foram classificados como `recovery`, não `approved`. Isso não estabelece uma propriedade garantida do sistema em população real. O controle A não é equivalente ao temporal B, nem qualquer um deles ao P1 aninhado.

**Porta desempenho por classe P0/A+B: verificada.** Integridade do GENESIS e do catálogo foi confirmada por execução local do usuário; a revisão exata original não foi registrada e permanece limitação explícita. Nenhuma métrica P1 por classe foi inferida.

## Deliberação formal de congelamento — 17/11/2026

**Decisão:** o responsável pela pesquisa autorizou expressamente congelar o pacote científico sintético P0/A, P0/B, P0/C (não identificável) e P1, junto dos relatórios de auditoria por classe A/B. Os hashes dos seis arquivos constituem suas identidades; nenhuma revisão retroativa é permitida. Novas execuções exigem nome, versão, hash e parecer separados.

**Exceção documentada:** não existe log inequívoco de `git rev-parse HEAD` no instante exato das execuções originais. Os commits de integração P0 (`69ae730`) e P1 (`3257208`) são comprovados pelo GitHub e os pulls locais pelo reflog, mas não constituem prova integral de proveniência do processo original.

**Validade científica:** apenas engenharia experimental e resultados sintéticos, sem inferência populacional, sem prova de generalização para coortes futuras independentes, sem promoção de modelos à produção. O P0/C permanece `not_identifiable`; o P1 não dispõe de recall individual por classe. Dados N4/ALN1/ALN2 não fazem parte deste congelamento. A EPIC operacional/P2 segue independente.

**Limite de execução:** esta decisão congela o registro científico e os identificadores SHA-256; não aplica permissões de arquivo, WORM ou travas físicas aos arquivos locais Windows. Preserve cópias de leitura e verifique periodicamente os hashes.
