# EPIC #77 — Parecer de execução P1 e portas restantes (17/11/2026)

**Tipo:** registro de evidência de execução, **não** manifesto de congelamento nem mudança de modelo.
**Origem:** relatório local `robustez_P1_v1.json`, fornecido pelo pesquisador, gerado por `epa.core_engine.mapa_robustness` após merge do PR #83. O JSON integral **não foi publicado neste PR**.

## Identificação da execução

| Campo | Valor |
|---|---|
| Schema | `epa.mapa.robustness.v1` |
| Classificação | `SYNTHETIC` |
| Alvo | `same_year_final_subject_outcome_3class` |
| Dataset manifest SHA-256 (declarado) | `0e61e8e65efa02d53bd40f13587c61b771f6667f392cc87b9733c59fcee8f4c6` |
| Relatório P1 SHA-256 (bytes recebidos) | `db2fe6d7ab6b920cd69489cb7dac5ed0722083701b8286dbe991476c7c3ec8c3` |
| Seeds | `20261029`, `20261030`, `20261031` |
| Cortes | N1, N2 e N3 |
| Split externo | `GroupShuffleSplit` por `student_id`, 30 estudantes treino / 10 teste por seed |
| Seleção interna | `GroupKFold` com 3 folds somente no treino externo |
| Modelos | Majoritário, Regressão Logística, Random Forest |
| Proveniência de execução | SHA do commit local, versões do ambiente e hashes dos arquivos fonte **ainda não registrados neste JSON** |

O arquivo registra os mesmos hashes de índices de treino/teste para cada seed ao longo de N1/N2/N3. Isso é coerente com reutilizar as mesmas partições por estudante em cada corte; **hashes não substituem auditoria independente dos IDs e dados brutos**. Os anos 2020–2026 aparecem tanto em treino quanto em teste: trata-se de avaliação **agrupada, não temporal**.

## Resultados observados — Macro-F1 em holdout externo (média ± desvio-padrão das 3 seeds)

| Corte | Majoritário | Regressão Logística | Random Forest |
|---|---:|---:|---:|
| N1 | 0,2343 ± 0,0111 | **0,7258 ± 0,0596** | 0,7196 ± 0,0377 |
| N2 | 0,2343 ± 0,0111 | **0,7748 ± 0,0687** | 0,7561 ± 0,0602 |
| N3 | 0,2343 ± 0,0111 | 0,8490 ± 0,0620 | **0,8700 ± 0,0585** |

**Gap médio Macro-F1 treino menos teste** (pontos absolutos na escala 0–1):

| Corte | Regressão Logística | Random Forest |
|---|---:|---:|
| N1 | 0,0683 | **0,1947** |
| N2 | 0,0781 | **0,1366** |
| N3 | 0,0559 | **0,0925** |

A Random Forest apresenta maior gap treino/teste em todos os cortes. É sinal de generalização inferior ao ajuste em treino, mas **não** demonstra isoladamente que a causa é sobreajuste, nem que as regularizações escolhidas são superiores às do baseline original.

**Controle negativo:** o treino com rótulos permutados diminuiu o Macro-F1 médio da Regressão Logística para 0,2658 / 0,2715 / 0,2673 em N1/N2/N3, e da Random Forest para 0,2990 / 0,2798 / 0,2943. Trata-se de **uma permutação por seed**, não de um teste formal de hipótese nem prova de ausência de vazamento. O majoritário é insensível à permutação, como esperado.

## Avaliação metodológica e limitações

1. Os valores P1 não devem ser comparados como estimativas diretamente equivalentes aos resultados P0/A (GroupKFold agrupado) ou P0/B (holdout de 2026), pois população de avaliação e partições são diferentes.
2. Os três holdouts externos de seeds distintas compartilham uma única população sintética. O desvio-padrão descreve dispersão observada, **não** intervalo de confiança populacional.
3. A queda de Macro-F1 mais intensa na seed `20261029` (em especial N3) não permite concluir que a classe `failed` seja a causa: o relatório P1 não contém matriz de confusão nem recall por classe.
4. O relatório inclui métricas de treino/teste e tentativas internas, mas não contém relógio de disponibilidade de rótulos para uma avaliação temporal; usar P0/B para esse objetivo.
5. A seleção de parâmetros da Random Forest usa 100 árvores e profundidade máxima 12, **configuração diferente** do MAPA P0. Não atribuir diferenças de score unicamente à regularização.
6. Os resultados são exclusivamente sintéticos e não demonstram desempenho em escolas reais, nem equivalem à regressão histórica N4 de ALN1/ALN2.

## Recursos existentes a reutilizar, sem duplicação

- `epa/core_engine/mapa_research.py`: métricas por classe e matriz de confusão em GroupKFold.
- `epa/core_engine/mapa_native_training.py`: função `scores` com recall, matriz de confusão e métricas probabilísticas.
- `epa/core_engine/mapa_statistical_evaluator.py`: reamostragem por estudante, múltiplas seeds e confiabilidade descritiva, **sobre artefatos de features próprios**, não sobre o JSON P1.
- `epa/core_engine/mapa_warning_audit.py`: auditoria de features ausentes e warnings do MLP, **não** classificação de warnings gerais de pytest.
- `docs/research/mapa-warning-audit-observed-and-mlp-experiment.md`: inventário histórico de `103 passed, 50 warnings` em outra execução/ambiente. Não confundir com eventuais `32 warnings` de outra suíte.
- `docs/research/EPIC_77_AUDITORIA_E_PLANO_DE_CONGELAMENTO.md`: matriz geral e separação das tarefas.

## Pendências verificáveis para congelamento científico

- [ ] Guardar localmente, fora do Git, os JSONs completos de P0/A/B/C e P1 junto com seus hashes; confirmar se os manifests indicam o **mesmo dataset** e se os hashes correspondem aos artefatos existentes.
- [ ] Registrar `git rev-parse HEAD`, versões de Python/NumPy/scikit-learn e hash do catálogo/script, sem reconstruir retrospectivamente a proveniência que o JSON original não guarda.
- [ ] Executar `python -m pytest -q` no checkout exato e **capturar/organizar os warnings da execução atual** por categoria, mensagem e origem. Não herdar a contagem de uma execução histórica.
- [ ] Revisar recall e matrizes por classe nas evidências P0/A/B; investigar a classe `failed` especificamente na dispersão P1 somente mediante evidência adicional **no mesmo split**, se estritamente necessário (não inferir a partir de outro protocolo).
- [ ] Revisar contratos de features point-in-time com SENTINEL e verificar que o holdout externo não foi empregado para selecionar os parâmetros.
- [ ] Decidir e documentar a condição de congelamento com os resultados negativos e limitações. **Não marcar EPIC #77 inteira como concluída**: infraestrutura e governança P2 permanecem em trilha própria.

## Próxima execução sugerida (Windows PowerShell)

```powershell
git switch develop
git status -sb
git rev-parse HEAD
python --version
python -m pip show numpy scikit-learn
python -m pytest -q tests/test_mapa_robustness.py tests/test_mapa_protocol_runner.py tests/test_mapa_warning_audit.py
```

A auditoria dos warnings da suíte atual deve ocorrer separadamente da auditoria específica do MLP. Não alterar modelos ou datasets somente para obter menos warnings.

**Conclusão provisória:** execução P1 concluída, métricas aritmeticamente consistentes, controles negativos coerentes e gap da Random Forest superior ao da Regressão Logística. Evidência ainda **não congelada** por falta de proveniência completa e classificação dos warnings da execução atual.
