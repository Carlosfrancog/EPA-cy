# GENESIS — primeira campanha comparativa observada (120 estudantes)

> **Natureza da evidência:** benchmark de engenharia com dados exclusivamente sintéticos; não constitui validação preditiva nem prova de desempenho em outros computadores. Fonte primária: `benchmark.json` enviado pelo executor local em 2026-11-12. O arquivo de origem fica fora do Git, pois os diretórios `data/` estão ignorados; os números abaixo são uma transcrição auditável das métricas observadas, não nova execução.

## Protocolo efetivamente executado

- Comando: `python tools/benchmark_genesis.py --students 120 --seed 20261029 --warmups 1 --repeats 3`
- Saída local de referência: `data/bench-1410ca6199c7/benchmark.json` (não versionada).
- Status final: `PASS`; 16 execuções com `return_code=0` e `parity_pass=true`.
- Catálogo: `examples/atlas.demo.json`; SHA-256 do catálogo **22457cc65857d43a33726e06380bc58dfb64b6e802b89c393c43cbf03bfa0ab1**.
- Windows 11 (`10.0.26200`), AMD64, 8 processadores lógicos, Python 3.13.3, psutil 7.2.2.
- Parâmetros: uma rodada de aquecimento, três rodadas medidas, amostragem RSS a cada 25 ms; `batch_students=1000`, `row_group_rows=4096`.
- Compilação release de Rust separada das medições (~3 min 34 s, observada no console).
- Por execução, cinco conjuntos logicamente iguais: 120 estudantes, 42 turmas, 840 matrículas, 324 ofertas de disciplinas e 25.920 registros bimestrais; comparação Parquet via `EXCEPT ALL` em ambas as direções e conferência SHA-256 por artefato.

## Medições brutas — excluindo aquecimento

| Motor | Rodada 1 (s) | Rodada 2 (s) | Rodada 3 (s) | Mediana (s) | RSS máximo amostrado (MiB) | Bytes Parquet |
|---|---:|---:|---:|---:|---:|---:|
| Python v3 / PyArrow | 3.7453383 | 3.5445111 | 3.5849663 | 3.5849663 | 90.36 | 168253 |
| Python v2 / DuckDB | 21.3689219 | 21.9886461 | 21.1430163 | 21.3689219 | 129.30 | 160097 |
| Rust → Python / PyArrow | 3.7629672 | 3.6734582 | 3.7529977 | 3.7529977 | 126.74 | 168253 |
| Rust nativo / ArrowWriter | 1.0054583 | 1.0043362 | 1.0519832 | 1.0054583 | 18.47 | 288755 |

O RSS é amostrado ao longo da árvore de processos; **não** é um pico absoluto garantido. As diferenças de tempo são relativas a este fluxo completo, com startup e gravação incluídos, mas sem compilação e sem custo de verificação posterior de paridade.

## Relações derivadas

- Aceleração relativa do Rust nativo sobre Python v3 = `3.5849663 / 1.0054583 ≈ 3.57×`.
- Aceleração relativa do Rust nativo sobre Python v2 = `21.3689219 / 1.0054583 ≈ 21.25×`.
- Redução relativa do RSS máximo amostrado frente ao Python v3 = `1 - 19365888 / 94748672 ≈ 79.56%`.
- O Parquet Rust nativo ocupa `288755 / 168253 ≈ 1.7162×` o tamanho do Parquet Python v3, ou **71.62% a mais**. O Python v2 produziu os menores arquivos nesta campanha (`160097` bytes).

## Interpretação e limitações

**Constatação:** Rust nativo apresenta a menor mediana de latência e o menor RSS observado desta campanha, e todos os motores reproduziram as mesmas entidades acadêmicas.

**Trade-off observado:** Rust gerou Parquet significativamente maior. Python v3 configura `compression="zstd"`; o writer Rust, na implementação aferida, chama `ArrowWriter::try_new(..., None)` sem uma configuração explícita equivalente de compressão e layout. Portanto, as condições físicas de persistência **não estão equiparadas**: não atribuir o tamanho final exclusivamente à linguagem, nem anunciar uma comparação justa da eficiência intrínseca de compressão.

**Limitações:** n=3 rodadas medidas; um computador; uma seed; um tamanho de dataset; execução de motores em ordem fixa; amostragem RSS de 25 ms; compilação excluída; variáveis de cache, aquecimento, disco, frequência e temperatura não controladas; sem intervalos de confiança, afinidade de CPU ou perfil exclusivo de CPU/I/O. Em bases maiores a relação pode mudar.

## Próxima campanha controlada (ainda não executada)

1. Uniformizar codec ZSTD, nível de compressão, contagem de linhas por row group e políticas de dicionário nos motores Python e Rust, sem alterar os registros nem os contratos científicos.
2. Revalidar `EXCEPT ALL`, hashes e contagens após cada alteração; **não** exigir hashes físicos iguais entre writers distintos.
3. Executar 30, 120, 500, 1000 e 2000 estudantes, com pelo menos 5 rodadas medidas e aquecimento, mantendo ambiente e catálogo fixos; conferir RAM/espaço antes da campanha.
4. Alternar ou randomizar a ordem dos motores entre rodadas, registrando CPU, RAM, disco e condições de execução.
5. Separar custo de geração, conversão JSON interna e escrita Parquet; explorar remoção da ponte JSON do Rust, preservando testes.
6. Complementar com auditoria real de consultas SQLite/Rails, operações DuckDB, `EXPLAIN`/`EXPLAIN ANALYZE`, volume lido, filtros, índices e perfil de ingestão.
7. Anexar logs/resultados completos como artefatos de pesquisa apropriados, versionando somente documentação e sumários quando os datasets `data/` forem intencionalmente ignorados.

## Caderno matemático — fórmulas adotadas

Seja `t_{m,r}` o tempo da rodada medida `r` para o motor `m`. Definimos:

`T_m = median(t_{m,1}, ..., t_{m,n})`.

`speedup(A/B) = T_B / T_A`; maior que 1 indica menor tempo de A para o mesmo fluxo.

`economia_RSS(A/B) = 1 - RSS_A / RSS_B`.

`excesso_armazenamento(A/B) = bytes_A / bytes_B - 1`.

Não inferir significância estatística a partir de n=3. Esse conjunto é um **baseline histórico** a ser comparado com a próxima campanha, não uma medição universal.
