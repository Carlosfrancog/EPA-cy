# Avaliador estatístico MAPA — fase anterior aos cadernos

## Objetivo

Estender o treinamento nativo **sem acoplamento ao Rails**: ler três feature Parquet imutáveis, formar holdouts por estudante e comparar modelos com o mesmo conjunto de teste, estatísticas de incerteza e qualidade probabilística.

## Comandos

```powershell
python -m pip install -e ".[dev,research]"
python -m pytest -q tests/test_mapa_statistical_evaluator.py
python -m epa.core_engine.mapa_statistical_evaluator `
  --features "data/mapa-features-25k-20261112-190953" `
  --max-students 500 `
  --models logistic_regression mlp `
  --seeds 20261029 20261030 20261031 `
  --bootstrap 200 `
  --output "data/mapa-statistical-500-v1.json"
```

## Protocolo

1. Mesmo subconjunto de alunos para todos os cortes N1/N2/N3, selecionado por SHA-256 com seed fixa de seleção.
2. Cada `seed` gera um novo holdout 75/25 de **IDs únicos de estudantes**. Todas as disciplinas e anos de um aluno ficam no mesmo lado.
3. Cada modelo é ajustado somente no lado de treino desse holdout, com hiperparâmetros congelados.
4. Probabilidades são alinhadas à ordem `approved, recovery, failed`. Macro-F1, recall por classe, log loss e Brier seguem o contrato MAPA.
5. Para cada corte e seed, bootstrap percentílico: sortear **IDs de alunos do teste com reposição** (n vezes, sendo n o número de alunos de teste), somar as matrizes de confusão individuais, recalcular macro-F1, obter percentis 2,5% e 97,5%.
6. Comparações pareadas usam **o mesmo sorteio de alunos** para ambos os modelos e calculam `F1_A - F1_B`. O valor `probability_delta_positive_in_bootstrap` é uma frequência descritiva, **não p-valor**.
7. Curvas de confiabilidade são produzidas por 10 intervalos para previsão mais provável e one-vs-rest. ECE é descritivo e dependente do binning; **nenhum ajuste de calibração é treinado sobre o teste**.

## Hipóteses e limitações

- **Lei dos Grandes Números:** registros do mesmo aluno são dependentes. A reamostragem por cluster ajuda a preservar dependência intra-aluno, mas o bootstrap percentílico ainda exige suposições de representatividade e independência entre clusters.
- Vários holdouts **na mesma população sintética** não equivalem a várias populações independentes. Esta fase estima estabilidade frente à divisão, não valida mudança de escola, população ou distribuição.
- Intervalos são **condicionais ao modelo treinado e à amostra de alunos no teste**. Não quantificam incerteza de treinamento/refit nem mudança de distribuição.
- Não comparar resultados repetidamente para otimizar modelos na mesma amostra e declarar o mesmo holdout 'teste final'. Para calibração de verdade, separar uma validação independente ou CV agrupada sem vazamento.
- Não afirmar superioridade estatística só porque um intervalo de delta exclui zero em uma configuração exploratória; corrigir multiplicidade e desenhar protocolo confirmatório se fizer inferência formal.
- Treinamento scikit-learn permanece em memória, máximo 5.000 estudantes. `fit_seconds` não inclui ETL, importação ou processamento bootstrap.
- Toda evidência é sintética, sem validação preditiva em escolas reais.

## Próximos gates para C01–C10

- CI Python verde, execução local de 500 alunos com múltiplas seeds.
- Perfis computacionais 500/2k/5k medindo RSS e tempo de execução completa.
- Experimentos entre populações sintéticas distintas e estabilidade por período/ano.
- Congelamento do contrato e de resultados antes de escrever as conclusões finais.

## Literatura

Gneiting & Raftery (2007), *Strictly Proper Scoring Rules, Prediction, and Estimation*, https://doi.org/10.1198/016214506000001437. Efron & Tibshirani (1993), *An Introduction to the Bootstrap*. scikit-learn, *Probability Calibration* https://scikit-learn.org/stable/modules/calibration.html.
