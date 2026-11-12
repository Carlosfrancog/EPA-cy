# MAPA / LUPA — auditoria de warnings e profiling diagnóstico

## Contexto e evidências observadas

Em execução local no Windows 11, Python 3.13.3, `python -m pytest -q` terminou **99 testes aprovados, 50 avisos**:

- **42 warnings `SimpleImputer`**: 36 em `tests/test_genesis_cohorts.py` e 6 em `tests/test_mapa_research_extended.py`. Mensagem: `Skipping features without any observed values: [5 6 7 8]`.
- **8 warnings `ConvergenceWarning`** em testes MLP: máximo de 300 iterações atingido sem convergência.

**Localização dos campos [5,6,7,8] (índices iniciados em zero), conforme `epa/core_engine/mapa.py`:** `prior_mean_grade`, `prior_attendance_rate`, `prior_absences`, `prior_unexcused_absences`. Em `feature_vector()`, esses campos são `NaN` se não houver registros anteriores da mesma disciplina. Isso é esperado para o primeiro ano de uma coorte independente; não imputar valores reais inexistentes ou usar informação futura.

**Configuração do MLP de pesquisa:** camadas ocultas (32,16), `max_iter=300`, `early_stopping=False`, `StandardScaler` e `SimpleImputer(strategy="constant", fill_value=0)`. O aviso confirma que não houve convergência declarada até o limite; sozinho não demonstra previsão ruim ou boa.

## Instrumento novo

`tools/audit_mapa_warnings.py` coleta **somente estatísticas agregadas** (sem IDs, notas ou registros por estudante) para cada corte N1/N2/N3:

- Quantidades observadas, ausentes e frações ausentes por feature na população de snapshots.
- Features totalmente ausentes **apenas no treino**, usando `GroupShuffleSplit` por estudante (sem cruzamento entre treino/teste).
- Contagens por classe em treino e teste.
- Diagnóstico exploratório do MLP: `n_iter_`, `loss_`, score de treino/teste, warnings capturados, número de features antes/depois do imputador.
- Tempo real isolado de geração sintética, construção de snapshots e ajuste do MLP. **Tempos de uma execução não são benchmark.**

Nenhum método matemático, hiperparâmetro, score de produção ou esquema de dataset foi alterado. A ferramenta não chama as rotas Rails nem executa SQL.

## Execução (após CI verde e merge)

```powershell
git switch develop
git pull origin develop
python -m pip install -e ".[dev,research,streaming,benchmark]"
python -m pytest -q tests/test_mapa_warning_audit.py
python tools/audit_mapa_warnings.py --students 24 --seed 13 --cutoffs 1 2 3 --output data/audit-mapa-24.json
```

Se `data/audit-mapa-24.json` existir, escolha um **nome novo** de saída; o script usa escrita exclusiva e não sobrescreve resultados. Enviar este JSON para confrontar as hipóteses e registrar a execução.

## Hipóteses e decisões ainda abertas

1. **Ausência estrutural de histórico:** confirmar por corte e por tipo de coorte. Nos casos com coluna totalmente ausente no treino, avaliar `keep_empty_features=True` com teste de não alteração de esquema e comparação empírica de métricas, ou remover explicitamente colunas não disponíveis apenas naquele corte. Não aplicar silenciosamente uma das duas opções.
2. **Não convergência do MLP:** antes de aumentar `max_iter`, medir curva `loss_curve_`, separação por classe, tamanho de amostra e resultados em múltiplas seeds. Aumentar iterações não é garantia de melhor generalização.
3. **Estabilidade de versão sklearn:** fixar dependências em ambiente de pesquisa reproduzível e distinguir comportamentos de versões na imputação.
4. **Profiling do pipeline:** a ferramenta cobre componentes Python em memória. A próxima etapa será perfilar tempos e volumes de `read_verified_v2()`, `duckdb.executemany`, `SELECT * FROM read_parquet(?)`, e instrumentar consultas SQLite/Rails e `EXPLAIN QUERY PLAN` em PR próprio.

## Limitações

Os dados e os rótulos são **SYNTHETIC**. A ausência de histórico no primeiro ano não deve ser interpretada como falha de coleta real; sem experimento confirmatório com coortes e dados reais, as métricas não estabelecem capacidade preditiva escolar. Os warnings apresentados são observados nos testes do usuário, enquanto os campos afetados e mecanismos possíveis decorrem da inspeção do código. Não declarar que a ferramenta foi executada localmente no hardware do usuário até receber o relatório.
