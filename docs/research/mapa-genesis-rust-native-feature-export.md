# P0 — GENESIS Rust nativo → MAPA: exportação de features (fase 1)

## Escopo entregue

`epa/core_engine/mapa_feature_export.py` lê o formato **`epa.genesis.dataset.rust_native.v1`**, valida SHA-256 e contagens dos cinco Parquet e os 17 checks SQL via `parquet_deep_audit.audit`. Em seguida valida presença dos quatro bimestres por matrícula/disciplina, prepara métricas em DuckDB (sem `fetchall` das tabelas originais) e produz:

- `N1.parquet`: corte após o primeiro bimestre;
- `N2.parquet`: após o segundo bimestre;
- `N3.parquet`: após o terceiro bimestre;
- `manifest.json`: origem SHA-256, seed, catálogo, onze features e hashes de saída.

É proibido reutilizar diretório de saída (artefatos imutáveis). A escrita usa diretório temporário e publicação após sucesso. Somente populações **sintéticas** são aceitas.

**Nota:** o SQL utiliza toda a série anual para calcular apenas o **rótulo final**, explicitamente separado das onze features. O histórico por disciplina é acumulado somente em anos anteriores, não inclui ano atual/futuro. A classificação segue limiares didáticos `approved >= 6`, `recovery >= 4`, `failed < 4`.

## Execução

```powershell
python -m pip install -e ".[dev,research]"
python -m pytest -q tests/test_mapa_feature_export.py

python -m epa.core_engine.mapa_feature_export `
  --dataset "data/rust-scale-<ID>/dataset" `
  --output "data/mapa-features-25k-01" `
  --memory-limit 512MB --threads 2
```

Substitua `<ID>` por um caminho **real** de execução, não use o placeholder literalmente. Cada saída inclui 3 x (period_records / 4) snapshots, desde que completa e consistente.

## Testes e limites

`tests/test_mapa_feature_export.py` compara todos os onze valores de features (tolerância numérica absoluta <= 1e-6), IDs, metadados e rótulos contra `student_timeline.build_snapshots` em três seeds. O fixture usa Parquet da v2 com **contrato de manifesto Rust nativo** para isolar as regras do pipeline. Isso **não substitui** um teste de integração com binário Rust; a paridade dos registros de entrada Rust vs Python deve continuar verificada separadamente.

Essa fase **não treina modelos** e **não converte magicamente o scikit-learn para treinamento out-of-core**. As próximas fases devem implementar leitor seguro do manifesto de features, split estável agrupado por estudante, uso de matriz de treino com limitação de memória, paridade das métricas MAPA e benchmarks 5k→10k→25k.

## Gates antes de usar na pesquisa

1. Testes Python e CI PASS.
2. Executar exportação real com dataset Rust (inicialmente 120/500, depois 5k).
3. Verificar integridade e comparar os três cutoffs com pipeline legado em pequenas escalas e múltiplas seeds.
4. Confirmar consumo máximo de memória e tempo na máquina de referência.
5. Somente após o encaixe no MAPA, iniciar benchmarks dos classificadores e produção de cadernos C01–C10.

Não aplicar a dados reais. Resultados sobre regras sintéticas do gerador não validam eficácia educacional.
