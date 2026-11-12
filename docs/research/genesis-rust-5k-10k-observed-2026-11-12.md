# GENESIS Rust — execução observada de 5.000 e 10.000 estudantes

**Data:** 2026-11-12. **Estado:** observações fornecidas pelo operador do laboratório Windows, não reprodução independente na CI. **Engine:** GENESIS Rust, streaming Arrow/Parquet. **Seed:** `20261029`. **Catálogo SHA-256:** `22457cc65857d43a33726e06380bc58dfb64b6e802b89c393c43cbf03bfa0ab1`. **Batch:** `row_group_rows=4096`, `sample_ms=25`, duas escolas, três turmas por série. Ambiente informado: Windows 11 10.0.26200, Python 3.13.3, oito CPUs lógicas.

## Evidência bruta

| Indicador | 5.000 | 10.000 |
|---|---:|---:|
| Status | PASS | PASS |
| Tempo total (s) | 27.26807440000266 | 57.25926519999484 |
| Observed peak RSS (bytes) | 41549824 | 35590144 |
| Amostras RSS | 708 | 1494 |
| Estudantes | 5000 | 10000 |
| Turmas | 42 | 42 |
| Matrículas | 35000 | 70000 |
| Ofertas de disciplinas | 324 | 324 |
| Registros bimestrais | 1080000 | 2160000 |
| Parquet estudantes (bytes) | 83544 | 166496 |
| Parquet turmas (bytes) | 2285 | 2285 |
| Parquet matrículas (bytes) | 943521 | 1886916 |
| Parquet ofertas (bytes) | 10719 | 10719 |
| Parquet registros bimestrais (bytes) | 10023819 | 20049190 |
| **Parquet total (bytes)** | **11063888** | **22115606** |
| Manifesto + arquivos SHA-256 verificados | Sim | Sim |
| Return code | 0 | 0 |

Os resultados foram obtidos em **uma rodada por escala**, portanto não há distribuição amostral ou estimativa de variância. Os tempos incluem startup do processo e geração + persistência, não compilação Rust. RSS amostrado não é garantia de pico real. O RSS observado menor em 10 mil estudantes que em 5 mil **não demonstra memória decrescente**; pode ser consequência de diferenças de amostragem/execução.

## Métricas calculadas

- Tempo por estudante: 5k ≈ **5,454 ms**; 10k ≈ **5,726 ms**.
- Tempo por registro bimestral: 5k ≈ **25,25 μs**; 10k ≈ **26,51 μs**.
- Razão de tempos `57.2592652 / 27.2680744 ≈ 2.1006`; razão de volume = 2. Escalabilidade aproximadamente linear no intervalo observado, não uma prova assintótica.
- Tamanho Parquet `11063888 / 1048576 ≈ 10,551 MiB`; `22115606 / 1048576 ≈ 21,091 MiB`.
- RSS amostrado `41549824 / 1048576 ≈ 39,625 MiB`; `35590144 / 1048576 ≈ 33,941 MiB`.
- Mantida a mesma configuração, **100k estudantes implicariam 21,6 milhões de registros bimestrais** e cerca de 221 MB de Parquet e 9–10 minutos de tempo extrapolado. Essas são **projeções incertas, não medições**; o disco e tempo reais podem divergir.

## Validação efetivamente realizada

`epa.benchmark.genesis_rust_scale.v1` confirma: cabeçalho do manifesto, catálogo, seed e número de estudantes, cinco entidades com contagens previstas e SHA-256 de cada arquivo persistido. Esse protocolo **não** realiza comparação semântica de todas as linhas com Python ou checagens referencial/estatística sobre cada registro, e por si só não comprova que as distribuições sejam plausíveis.

## Próximos gates

1. Avaliar os datasets de 5k e 10k via DuckDB com consultas agregadas, sem materializar milhões de linhas em listas Python: contagens por disciplina, intervalos de notas, frequência de presença, classes de reprovação/recuperação e integridade referencial.
2. Repetir cada escala pelo menos três vezes com diretórios distintos para avaliar dispersão de tempo e RSS. Comparar row groups 4096/8192/16384 quando instrumentação estiver disponível.
3. Escalar progressivamente a 25k e 50k, acompanhando espaço de armazenamento e a evolução das métricas; só então executar 100k.
4. Construir teste de determinismo por prefixo/paridade com a referência Python até 2k e entre saídas Rust de 2k e 10k na mesma seed, mais validação de relações entre tabelas acima de 2k.
5. Identificar custos CPU/Arrow/Parquet e remover `serde_json::Value` da gravação nativa em PR separado, sempre preservando golden vectors.
6. Manter separação entre engenharia da geração sintética e validade externa de treinamento MAPA. Mais registros sintéticos não equivalem a estudantes independentes observados.

**Conclusão:** geração Rust de 10 mil estudantes reportou PASS no protocolo de integridade de arquivos e contagens com consumo de memória amostrado baixo. Aumento de 5k→10k apresenta tempo aproximadamente linear. Não afirmar paridade linha a linha com Python acima de 2k nem afirmar capacidade comprovada de 100k ainda.
