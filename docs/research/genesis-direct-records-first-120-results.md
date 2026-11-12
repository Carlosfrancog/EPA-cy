# EPA — GENESIS Rust callback: campanha 120 estudantes e regressão LUPA

## Evidência observada (12/11/2026)

Origem: saída de console enviada pelo operador no Windows após merge do PR #55. O arquivo `data/bench-f3fe8e11341e/benchmark.json` foi criado **localmente**, mas não foi anexado nesta etapa; portanto, este documento registra somente os valores visíveis no console.

Comando:

```powershell
python tools/benchmark_genesis.py --students 120 --seed 20261029 --warmups 1 --repeats 5 --engines python_v3_pyarrow rust_native_parquet
```

Parâmetros: 120 estudantes, seed 20261029, 1 aquecimento, 5 repetições, Windows. Compilação release concluída antes do benchmark, em 0,60 s. Cada comparação Parquet reportou `PASS` nas cinco entidades, sem diferença de linhas (`only_left=0` e `only_right=0`): 120 estudantes, 42 turmas, 840 matrículas, 324 ofertas e 25.920 registros bimestrais. Status final: `PASS`.

| Rodada | Python v3 (s) | Rust nativo sem JSONL (s) |
|---|---:|---:|
| Aquecimento (excluído) | 3.656 | 0.616 |
| 1 | 3.596 | 0.634 |
| 2 | 3.468 | 0.614 |
| 3 | 3.471 | 0.639 |
| 4 | 3.431 | 0.701 |
| 5 | 3.434 | 0.600 |
| **Mediana** | **3.468** | **0.634** |

O Rust nativo apresentou `3.468 / 0.634 ≈ 5.47×` aceleração sobre o Python v3 nessa campanha.

A campanha anterior (pré-PR #55) registrou mediana Rust nativo **1,0054583 s** com três repetições. Comparando medianas das duas campanhas, a nova mediana de **0,634 s** representa aproximadamente **36,9% menos tempo**, ou **1,59×** de aceleração frente ao Rust antigo. É comparação **indicativa, não teste A/B pareado**: diferem quantidade de rodadas e condições temporais de execução; um experimento cruzado na mesma sessão controlada seria mais forte.

RSS informado por rodada: Python v3 aproximadamente 89,7–90,2 MiB; Rust nativo aproximadamente 17,9–18,1 MiB. Os valores foram arredondados pelo console. Não houve medição física de bytes Parquet no material novo enviado; **não afirmar** melhora de compressão ou tamanho nesta campanha.

## Integridade e teste geral

- `cargo test --locked --manifest-path engines/genesis-rs/Cargo.toml`: **14 passaram, 0 falharam**.
- `python tools/check_genesis_rust_stream.py --students 10 --seed 42`: **PASS**, 2.606 linhas lógicas comparadas.
- Com seed 20261029: **PASS**, 2.606 linhas comparadas.
- `python -m pytest -q`: **96 passaram, 3 falharam**, 50 warnings; todas as três falhas são em `tests/test_lupa.py`. O erro é `ValueError: pos_label=1 is not a valid label` ao avaliar macro-F1 com classes textuais `approved`, `failed`, `recovery` via `make_scorer` / `sklearn.metrics`.
- A correção proposta altera **apenas a forma de fornecer a função de score** ao `permutation_importance`, utilizando macro-F1 diretamente a partir de `predict`, mantendo labels e `zero_division=0`; não altera alvo, splits ou modelos.

## Próxima validação

1. Confirmar que o PR de compatibilidade LUPA passa na CI e, depois do merge, rodar `python -m pytest -q tests/test_lupa.py` e `python -m pytest -q` no Windows Python 3.13.3.
2. Anexar o `benchmark.json` da nova campanha para conferir hashes, bytes Parquet e ambiente completos.
3. Repetir benchmark controlado com 500/1000/2000 estudantes; depois avaliar compressão ZSTD e a substituição de `serde_json::Value` por linhas tipadas.
4. Preservar a distinção entre paridade de datasets **sintéticos**, desempenho de engenharia e validade científica preditiva externa.

**Conclusão provisória:** o caminho de registros estruturados do Rust apresenta redução expressiva de latência no cenário amostrado, mas o teste geral Python ainda não está totalmente verde no computador local enquanto a compatibilidade LUPA não for corrigida e validada.
