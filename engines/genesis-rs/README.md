# GENESIS Core Rust — etapa 1

Esta etapa adiciona a base do motor Rust ao EPA **sem alterar os geradores Python**.

## Executar no Windows (raiz do repositório)

```powershell
cargo test --manifest-path engines/genesis-rs/Cargo.toml
cargo run --release --manifest-path engines/genesis-rs/Cargo.toml -- seed 20261029 SYN00000001 profile
cargo run --release --manifest-path engines/genesis-rs/Cargo.toml -- inspect examples/atlas.demo.json 120 20261029
```

A derivação da seed replica `epa.genesis.v2.stable_seed`: SHA-256 do texto UTF-8 unido por `|`, lendo os primeiros oito bytes como inteiro big-endian sem sinal.

Vetores de teste extraídos da implementação Python:
- `20261029|SYN00000001|profile` → `3051383292237719500`
- `20261029|SYN00000001|2020|section` → `17544070759066566074`

A inspeção do catálogo demonstra as quantidades esperadas com **configuração padrão** de duas escolas, três turmas por série e quatro períodos por ano.

**Limites:** ainda não há geração de notas/frequência, equivalente MT19937+gauss do Python, paralelismo ou gravação Parquet. Nenhum ganho de velocidade é alegado nesta etapa.

## Próximos passos

1. Golden tests comparando amostras dos registros v2/v3.
2. Implementar compatibilidade do RNG Python e suas distribuições (incluindo arredondamento).
3. Escrita Parquet incremental e manifestos versionados.
4. Benchmarks de tempo, memória e escalabilidade, sempre com saídas imutáveis.
