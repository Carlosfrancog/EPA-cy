# MAPA — fechamento da auditoria 103/103 e experimento controlado MLP

## Evidência observada, Windows 11, Python 3.13.3

O usuário executou a auditoria `epa.research.mapa_warning_audit.v1` com `students=24`, `seed=13`, `atlas.demo.json`, cortes N1/N2/N3. O script reportou 1296 snapshots em cada corte; nenhuma feature atual ausente; **264/1296 (20,37037%)** ausências nas quatro features `prior_mean_grade`, `prior_attendance_rate`, `prior_absences`, `prior_unexcused_absences` em cada corte. `all_missing_train_features=[]`; a matriz de entrada e saída do `SimpleImputer` manteve 11 colunas nesta amostra.

| Corte | MLP n_iter / max_iter | Perda final | Acurácia treino | Acurácia teste |
|---|---|---:|---:|---:|
| N1 | 300 / 300 | 0.2845077301 | 0.8765432099 | 0.8395061728 |
| N2 | 300 / 300 | 0.1856757824 | 0.9259259259 | 0.8827160494 |
| N3 | 300 / 300 | 0.1123581531 | 0.9567901235 | 0.9074074074 |

O MLP gerou `ConvergenceWarning` em todos os cortes. Os números acima são de **uma execução** de diagnóstico, não estimativas de eficácia em escolas reais.

A suíte local completa reportou **103 passed, 50 warnings** em 82,52 s: 42 warnings sobre colunas 5–8 inteiramente ausentes em certas coortes de testes e 8 warnings de não convergência MLP. Os dados faltantes em uma coorte inicial não indicam necessariamente erro; manter a forma de entrada exige `keep_empty_features=True` ou política explícita equivalente.

## Novo experimento exploratório, separado dos baselines

`epa/core_engine/mapa_mlp_convergence.py` e `tools/experiment_mlp_convergence.py` propõem avaliação de orçamento de iterações `(300,600,1000)` em **split interno por estudante** e teste externo reservado:

1. `GroupShuffleSplit` 75/25 por estudante reserva holdout externo.
2. Um segundo `GroupShuffleSplit` cria treino e validação dentro do treino externo.
3. Treinar as três configurações pré-definidas no treino interno (mesma seed e arquitetura), registrar warnings, `n_iter_`, perda e macro-F1 de validação; nunca selecionar pelo holdout externo.
4. Escolher maior macro-F1 de validação, desempatar por menor `max_iter`; retreinar somente a configuração escolhida sobre o treino externo inteiro.
5. Avaliar o holdout externo uma única vez e reportar suporte por classe, acurácia e macro-F1.
6. Usar `SimpleImputer(keep_empty_features=True)` **apenas neste experimento**, de modo que a entrada preserve exatamente as 11 features mesmo em coortes sem histórico.

O resultado é exploratório e não altera `mapa_extended.py`, relatórios existentes, modelos, datasets nem decisões de produção.

## Execução proposta após CI verde e merge

```powershell
git switch develop
git pull origin develop
python -m pytest -q tests/test_mapa_mlp_convergence.py
python -m pytest -q
python tools/experiment_mlp_convergence.py --students 24 --seed 13 --cutoffs 1 2 3 --output data/mlp-convergence-24.json
```

A saída é exclusiva (`x`), sem sobrescrever arquivos antigos. Enviar `data/mlp-convergence-24.json` antes de qualquer modificação de hiperparâmetros. É possível rodar novas sementes em arquivos separados para verificar estabilidade; evitar adaptar parâmetros ao holdout após ver os resultados.

## Limitações e inferências

- O score externo é **um único holdout sintético**, não comprovação de generalização.
- N1, N2 e N3 mudam a quantidade de informação disponível. Desempenho maior em N3 não prova que o MLP melhora com treinamento prolongado.
- `n_iter_=max_iter` e `ConvergenceWarning` significam falta de convergência segundo o critério do solver, não necessariamente overfitting nem baixa acurácia.
- O experimento muda a política de manutenção de colunas vazias em comparação com o baseline; comparar scores como **ablação exploratória**, não como ganho isolado de iterações.
- A comparação do efeito de iterações deve considerar macro-F1 de validação e suporte por classe, especialmente a classe `failed`.
- Profiling SQL Rails/SQLite e DuckDB continua pendente, em etapa separada, para não misturar preocupações.
