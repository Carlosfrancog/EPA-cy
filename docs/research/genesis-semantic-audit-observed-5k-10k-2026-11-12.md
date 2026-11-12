# GENESIS Rust — resultados observados da auditoria semântica 5k/10k (2026-11-12)

## Procedência e método

Relatórios JSON `epa.genesis.parquet_deep_audit.v1` fornecidos pelo operador em Windows 11, após geração dos datasets Rust com seed `20261029` e catálogo SHA-256 `22457cc65857d43a33726e06380bc58dfb64b6e802b89c393c43cbf03bfa0ab1`. Dados **SYNTHETIC**. São resultados **informados**, não reexecutados neste PR.

A auditoria DuckDB realizou verificação SHA-256 por arquivo, contagem por entidade, 17 checks SQL de chaves, vínculos, consistência de ano/série/área, notas e frequência; reportou agregados por período e área.

## Evidência

| Medida | 5.000 estudantes | 10.000 estudantes |
|---|---:|---:|
| Status | PASS | PASS |
| Checks aprovados | 17/17 | 17/17 |
| Checks com valores não zero | 0 | 0 |
| Estudantes | 5000 | 10000 |
| Turmas | 42 | 42 |
| Matrículas | 35000 | 70000 |
| Ofertas | 324 | 324 |
| Registros bimestrais | 1080000 | 2160000 |
| SHA-256 dos cinco Parquet | verificado | verificado |
| Média de nota | 6.104646888888809 | 6.09468910185182 |
| Média de frequência | 0.8760527316290122 | 0.8761099017123118 |
| Mínimo de frequência observado | 0.190476 | 0.190476 |
| Máximo de frequência observado | 1.0 | 1.0 |
| Nota mínima/máxima | 0.0/10.0 | 0.0/10.0 |
| Disciplinas distintas | 11 | 11 |
| Anos distintos | 7 | 7 |

`term_counts`: 5k = 270.000 observações em cada um dos quatro períodos; 10k = 540.000 em cada período.

`by_knowledge_area`:

| Área | 5k | 10k |
|---|---:|---:|
| HUMANAS | 400000 | 800000 |
| LINGUAGENS | 280000 | 560000 |
| MATEMATICA | 140000 | 280000 |
| NATUREZA | 260000 | 520000 |

Nenhum dos 17 checks SQL reportou problemas. Em particular, não foram observadas duplicidades de chaves, referências faltantes ou inconsistências das taxas de presença/ausência.

## Interpretação

1. Os arquivos passam **nos invariantes efetivamente programados**. Hashes verificam integridade física, e os checks DuckDB acrescentam evidência sobre semântica. Nenhum dos dois comprova todas as regras de geração possíveis.
2. As médias de notas/frequência permanecem próximas entre as duas escalas. Como ambos os datasets usam mesma seed e algoritmo, não interpretar isso como demonstração de validade estatística ou independência experimental.
3. Taxa de frequência observada mínima 0.190476 **não contradiz necessariamente** a probabilidade individual geradora limitada a 0.30, pois presenças são amostradas em um número finito de sessões.
4. A auditoria não realiza paridade linha a linha com Python acima de 2.000 estudantes, não mede generalização do MAPA nem torna dados sintéticos equivalentes a históricos reais.
5. Na fase anterior, os benchmarks Rust-only foram 27,268s / 39,6 MiB RSS amostrado (5k) e 57,259s / 33,9 MiB (10k). RSS amostrado não é pico absoluto e uma execução por escala não estabelece intervalos de confiança.

## Próximo gate operacional

Executar **25.000 estudantes** com o benchmark Rust-only existente, antes de iniciar a refatoração tipada:

```powershell
python tools/benchmark_genesis_rust_scale.py --students 25000 --seed 20261029
```

Depois auditar o novo diretório real em `data/rust-scale-*/dataset` usando:

```powershell
python tools/audit_genesis_parquet.py --dataset "data/rust-scale-<ID>/dataset" --output "data/audit-genesis-25k.json"
```

Volume projetado: **5.400.000 registros bimestrais**; não é volume ainda medido. Se `PASS`, registrar tempo, RSS e tamanho de Parquet, repetir execução para variabilidade, e avançar a 50k conforme recursos disponíveis.

A otimização seguinte será uma implementação de registros Rust tipados e builders Arrow sem `serde_json::Value` no caminho nativo, com **paridade até 2k (Python) e determinismo por prefixo em maior escala** antes de substituir a implementação atual.

**Escopo deste PR:** documentação apenas. Nenhum modelo ML, geração ou auditoria é alterado.
