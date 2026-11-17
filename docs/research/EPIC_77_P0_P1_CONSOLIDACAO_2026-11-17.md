# EPIC #77 — Manifesto de evidências P0/A-B-C e P1 (provisório)

**Estado:** PROVISIONAL_NOT_FROZEN. Registro derivado dos quatro JSONs enviados pelo pesquisador, comparados bit a bit com os hashes da listagem local. Não modifica treinamento, relatórios, CODE ou N4.

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

## Gates faltantes antes do freeze

1. Rastrear commit exato da execução, ou registrar explicitamente que é desconhecido; revisar versões por artefato.
2. Conferir a integridade dos artefatos físicos e o catálogo GENESIS contra o `manifest.json` original.
3. Verificar suporte e recall por classe em resultados do CORE apropriados, sem extrapolar esse diagnóstico para splits diferentes.
4. Preservar relatórios originais com hashes e registrar limitações metodológicas e warnings no parecer final.

O manifesto estruturado está em `docs/research/EPIC_77_EVIDENCE_MANIFEST_v1.json`. A EPIC operacional/P2 não está encerrada e nenhuma evidência de alunos reais integra este pacote.
