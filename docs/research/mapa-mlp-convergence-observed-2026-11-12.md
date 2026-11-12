# MAPA — Resultado observado do experimento exploratório de convergência MLP

**Data:** 2026-11-12. **Fonte:** JSON `epa.research.mlp_convergence.v1` enviado pelo executor local Windows; esta é uma transcrição da evidência fornecida, não uma nova execução. Dados e rótulos são exclusivamente **SYNTHETIC**, 24 estudantes, seed 13, `atlas.demo.json`, cortes N1/N2/N3.

## Protocolo informado

O experimento usa um holdout externo agrupado por estudante (18 no treino externo, 6 no teste), subdividindo os 18 estudantes em 13 para ajuste e 5 para validação interna. Compara `max_iter = {300, 600, 1000}` usando macro-F1 na validação interna; somente depois de selecionar a configuração executa um novo ajuste nos 18 estudantes e avalia os 6 externos. O imputador experimental preserva as 11 features (`keep_empty_features=True`).

## Medições informadas

| Corte | Iterações | Macro-F1 validação | Loss treino interno | Fit interno (s) | ConvergenceWarning |
|---|---:|---:|---:|---:|---|
| N1 | 300 | 0.7065079365 | 0.2256353801 | 0.706 | Sim |
| N1 | 600 | 0.6663526077 | 0.1614789563 | 1.437 | Sim |
| N1 | 1000 | 0.6762901871 | 0.1017790183 | 2.381 | Sim |
| N2 | 300 | 0.8151398590 | 0.1573698096 | 0.712 | Sim |
| N2 | 600 | 0.8071074879 | 0.1073814794 | 1.376 | Sim |
| N2 | 1000 | 0.8121971614 | 0.0593166346 | 2.359 | Sim |
| N3 | 300 | 0.8449388976 | 0.0997908727 | 0.673 | Sim |
| N3 | 600 | 0.8337628224 | 0.0617972547 | 1.438 | Sim |
| N3 | 1000 | 0.8000136114 | 0.0291987074 | 2.368 | Sim |

Em todos os cortes, a seleção interna escolheu `max_iter=300`; em todas as configurações, `n_iter_ = max_iter` e houve `ConvergenceWarning`. Uma loss de treinamento menor com 600 ou 1000 iterações **não se traduziu em aumento de macro-F1 de validação** neste split. Isso é evidência de benefício não demonstrado, **não prova isolada de overfitting**.

## Retreino e avaliação externa — somente configuração selecionada

| Corte | Iterações selecionadas | Macro-F1 teste | Acurácia teste | Loss final |
|---|---:|---:|---:|---:|
| N1 | 300 | 0.7450684731 | 0.8395061728 | 0.2845077301 |
| N2 | 300 | 0.8259262942 | 0.8827160494 | 0.1856757824 |
| N3 | 300 | 0.8566419467 | 0.9074074074 | 0.1123581531 |

A distribuição de suporte no holdout externo é idêntica nos cortes: `approved=214`, `recovery=93`, `failed=17` (324 observações). Há **somente seis estudantes externos**; observações por disciplina não são independentes. A raridade de `failed` recomenda reportar recall/F1 por classe, matriz de confusão e intervalos por cluster antes de conclusões acadêmicas sobre o risco de reprovação.

## Decisões e limites

1. **Manter o baseline atual de 300 iterações sem mudança de hiperparâmetro**, enquanto não houver evidência multi-seed de que novo valor melhora macro-F1.
2. Não suprimir `ConvergenceWarning`: ele informa que o critério do otimizador não foi atingido, ainda que a métrica de validação seja útil.
3. O experimento mudou `keep_empty_features=True` em relação ao pipeline de referência; essa modificação deve ser isolada em ablação posterior.
4. Repetir em várias seeds e coortes sintéticas independentes, fixando previamente o protocolo e preservando a separação agrupada por estudante; executar análise de estabilidade sem escolher valores pelo holdout externo.
5. Investigar `loss_curve_`, `tol`, `n_iter_no_change`, curvas de aprendizado e early stopping **apenas em treino/validação interna**; avaliar custo computacional e macro-F1.
6. Incluir `recall_by_class`, `f1_by_class`, matriz de confusão e tamanhos de suporte por aluno e classe, de maneira agregada, para não esconder baixa sensibilidade da classe `failed`.
7. Auditoria de consultas SQLite/Rails e DuckDB, bem como profiling detalhado do Rust, continuam como trilhas distintas.

**Restrição fundamental:** este único experimento com 24 estudantes sintéticos e seed 13 não valida o modelo em escolas reais, não permite alegar significância estatística e não fundamenta promessa de acerto operacional.
