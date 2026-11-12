# GENESIS Core Rust — etapa 2: aleatoriedade compatível com Python

O mecanismo `rng.rs` replica o fluxo **MT19937** de `random.Random(<u64>)` do CPython para as operações usadas no GENESIS: `random()`, `uniform()`, `gauss()` (com cache) e `randint()` com amostragem por rejeição.

## Validação

Na raiz do repositório:

```powershell
cargo test --manifest-path engines/genesis-rs/Cargo.toml
cargo run --release --manifest-path engines/genesis-rs/Cargo.toml -- seed 20261029 SYN00000001 profile
cargo run --release --manifest-path engines/genesis-rs/Cargo.toml -- inspect examples/atlas.demo.json 120 20261029
cargo run --release --manifest-path engines/genesis-rs/Cargo.toml -- rng-probe 3051383292237719500
```

Vetores de referência gerados com Python `random.Random(seed)`:
- `random()` após seed `3051383292237719500` → `0.020478941183366572`
- `uniform(-1.65, 1.65)` após a mesma seed → `-1.5824194940948901`
- `gauss(0, 0.95)` após seed `16817751025044115065` → `0.16693285048241108`
- `randint(16, 25)` após essa seed → `21`

O `rng-probe` consome uma única sequência contínua; seu segundo valor não é o primeiro `uniform` de uma instância recém-inicializada.

## Limitações

- Compatibilidade destinada a seeds derivadas como inteiros positivos de 64 bits; não cobre todos os tipos de seed do Python.
- Pode haver pequenas diferenças de arredondamento entre bibliotecas matemáticas/arquiteturas, especialmente em `gauss`.
- Esta etapa ainda **não gera registros Parquet** nem calcula notas escolares; o código antigo Python permanece como referência.
- A paridade lógica dos registros v2/v3 já foi testada separadamente; a paridade da futura geração Rust dependerá de novo teste de ponta a ponta.

Os testes unitários executam automaticamente em Windows e Linux por GitHub Actions.

## Etapa 3 — geração longitudinal em streaming (JSONL)

O comando abaixo emite uma linha JSON por entidade/registro, sem acumular todo o conjunto em memória:

```powershell
cargo run --release --manifest-path engines/genesis-rs/Cargo.toml -- generate-jsonl examples/atlas.demo.json 3 20261029 > data/genesis-rs-3.jsonl
```

Esse arquivo **não é** Parquet nem um dataset de treinamento validado. Não reutilize diretórios ou artefatos das campanhas anteriores.

Comparação direta com o gerador Python v3 (sem gravar arquivos):

```powershell
$env:PYTHONPATH = "."
python tools/check_genesis_rust_stream.py --students 3 --seed 20261029
python tools/check_genesis_rust_stream.py --students 10 --seed 42
```

O comparador confronta todos os registros, campos e tipos. Usa tolerância absoluta 1e-10 somente para valores `float`; campos inteiros/textuais são exatos. Se houver diferença de nota arredondada, frequência ou integridade, o comando falha. A etapa ainda **não tem métricas de performance comparáveis à v3**, pois JSONL e Parquet possuem custos de I/O distintos.

Para validar o código novo:

```powershell
cargo test --locked --manifest-path engines/genesis-rs/Cargo.toml
```

A evolução da pesquisa, auditoria de SQL/consultas e entregáveis completos estão em `docs/research/engineering-evidence-plan-2026-11-12.md`.
