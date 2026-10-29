# ADR-002 — DuckDB + Parquet na base analítica

- Status: Aceito
- Contexto: históricos escolares podem alcançar escala elevada e requerem consultas por coluna, ano e estudante.
- Decisão: preservar dados analíticos em Parquet versionado e processá-los com DuckDB; particionar por critérios documentados sem fragmentar indevidamente o dataset.
- Consequências: não usar o banco operacional como repositório de todas as avaliações. Workers escrevem saídas isoladas, verificadas antes de promover novas versões; não compartilhar arquivo DuckDB em escrita irrestrita.
- Verificação: leitura de partições, conferência de digest e consultas reproduzíveis.
