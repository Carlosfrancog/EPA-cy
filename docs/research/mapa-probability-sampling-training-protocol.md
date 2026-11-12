# MAPA — Fase 2: treinamento limitado e probabilístico (pesquisa)

## Pergunta experimental

A geração GENESIS Rust passou a produzir grandes populações sintéticas, mas a **capacidade de geração não prova capacidade de treinamento**. Este protocolo avalia tempo de ajuste e desempenho de modelos nos conjuntos de features N1/N2/N3 exportados em Parquet, preservando um conjunto de alunos de teste exclusivo e evitando materializar três cutoffs ao mesmo tempo.

## Ferramenta

```powershell
python -m pip install -e ".[dev,research]"
python -m pytest -q tests/test_mapa_native_training.py
python -m epa.core_engine.mapa_native_training `
  --features "data/mapa-features-25k-20261112-190953" `
  --max-students 500 `
  --models majority logistic_regression `
  --seed 20261029 `
  --output "data/mapa-native-500-baselines.json"
```

`--max-students` controla o **número de IDs de aluno**, não de linhas de treino, e está limitado a 5.000 nesta versão. Para estudos maiores, medir os custos primeiro, depois ajustar o limite mediante evidência. O subconjunto é selecionado por SHA-256 de `seed|student_id` (amostragem determinística, não verdadeiramente aleatória), sem materializar todos os registros em Python. É feita **uma única separação GroupShuffleSplit de IDs de aluno**, reutilizada para N1, N2 e N3; as linhas de cada aluno permanecem do mesmo lado da divisão.

`--models` também aceita `random_forest` e `mlp`. Evitar iniciar com esses algoritmos em grande volume: o Random Forest usa 200 árvores e o MLP pode levar muito tempo ou emitir aviso de não convergência. A versão atual é in-memory para a matriz limitada e não implementa `partial_fit`.

## Métricas e matemática

- **Lei dos Grandes Números:** exige condições sobre o processo amostral, e não transforma 1,35 milhão de linhas de uma mesma população em 1,35 milhão de unidades independentes. Existem 25.000 alunos e múltiplas observações correlacionadas por aluno. A divisão por aluno é indispensável para reduzir vazamento entre treino e teste.
- **Probabilidade condicional:** `predict_proba` deve ser interpretada como previsão estimada da distribuição de classes. As colunas são reordenadas segundo a lista fixa `(approved, recovery, failed)` antes da pontuação, inclusive se a classe de treino estiver ausente.
- **Log loss multiclasses:** `-mean(log P(classe verdadeira))`, penaliza confiança incorreta. É uma *proper scoring rule*.
- **Brier multiclasses:** `mean_i sum_k (p_ik - 1[y_i=k])²`; menor é melhor, entre 0 e 2 para três classes. **Não** confundir valor com acurácia ou afirmar que Brier isoladamente prova calibração.
- **Macro-F1 e recall por classe:** pesos iguais às três classes reportadas, inclusive recuperação/reprovação; matriz de confusão em ordem fixa.
- **Tempo de fit:** `perf_counter()`, não inclui todo o processo de leitura, benchmark de memória ainda pendente.

## Limitações metodológicas e gates

1. O gerador usa regras sintéticas; nenhum resultado valida escolas reais.
2. Uma população/seed e um holdout não comprovam generalização. Mais adiante executar coortes independentes, testes por escola/tempo e intervalos de incerteza reamostrando **alunos**, não linhas.
3. Calibração será uma etapa posterior com divisão independente de treino, calibração e teste ou CV agrupada: calibrar no conjunto de teste seria vazamento.
4. O código verifica os hashes dos três Parquet, manifesto e os nomes das 11 features antes de treinar. A CI usa fixture pequena com contrato de formato nativo simulado; executar também sobre dataset Rust real.
5. `GroupShuffleSplit` não é estratificação por estudante; reportar suporte por classe e não usar só acurácia.
6. Conectar métricas científicas ao artigo v0.3 apenas após CI PASS, validação de dados e benchmark reproduzido.

## Referências matemáticas e estatísticas

- Gneiting, T.; Raftery, A. E. (2007). **Strictly Proper Scoring Rules, Prediction, and Estimation**. *Journal of the American Statistical Association*. https://doi.org/10.1198/016214506000001437
- Gneiting, T.; Balabdaoui, F.; Raftery, A. E. (2007). **Probabilistic forecasts, calibration and sharpness**. *Journal of the Royal Statistical Society: Series B*, 69(2), 243–268. https://doi.org/10.1111/j.1467-9868.2007.00587.x
- Scikit-learn, **Probability calibration**: https://scikit-learn.org/stable/modules/calibration.html
- Scikit-learn, **GroupKFold**: https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GroupKFold.html
- Scikit-learn, **Model evaluation**: https://scikit-learn.org/stable/modules/model_evaluation.html

Essas referências justificam métricas e validações, **não garantem melhorias de F1**. Conceitos físicos como entropia têm analogias matemáticas úteis; propor uma 'lei física da predição escolar' sem hipótese e teste seria metodologicamente injustificado.
