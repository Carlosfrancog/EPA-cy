# ADR P0 — GENESIS v3, Rails–DuckDB e SENTINEL

Status: protótipo para revisão na branch develop. Não homologado em produção.

## Contratos de arquitetura

- Preservar Rails + SQLite para metadados de jobs, sem importar milhões de linhas de histórico para ActiveRecord.
- GENESIS v3 gera os mesmos registros lógicos de GENESIS v2 e escreve os cinco artefatos Parquet com PyArrow ParquetWriter, em row groups de tamanho fixo. Um arquivo Parquet só recebe novos row groups enquanto o writer está aberto, não após seu fechamento.
- Cada estudante, ano, disciplina e bimestre utiliza seeds independentes derivadas de SHA-256. O ID do lote não participa da seed.
- Um dataset somente é publicado quando os cinco Parquet e o manifesto foram fechados; versões já publicadas não são sobrescritas.
- Rails consulta dados agregados em processo DuckDB CLI separado, com entradas validadas, SQL limitado, SHA-256 checado e limites de tempo e memória.
- O SENTINEL recusa features que não possam ser recomputadas a partir de dados conhecidos até N1, N2 ou N3. Registra DENY sem modificar o manifesto ou seu hash original.
- TabPFN e GNN não são introduzidos nesta etapa.

## Escala e limites

Para 20.000 estudantes com o catálogo demonstrativo: 140.000 matrículas, 1.080.000 unidades disciplina/ano, 4.320.000 registros bimestrais; até 3.240.000 snapshots dos três recortes. Números projetados, não benchmarks executados.

O buffer de dados em memória é limitado por --row-group-rows em cada tabela, independentemente de --batch-students. A coleta de lixo é uma medida complementar; não é a garantia de RAM. A identidade lógica dos registros é registrada em logical_sha256, diferente do hash físico dos arquivos Parquet. Dois manifestos podem ser diferentes se os tamanhos de lote diferirem.

## Execução

1. Instalar dependências: python -m pip install -e ".[dev,research,streaming]"
2. Gerar conjunto: python -m epa.genesis.v3 --output data/datasets/epa-v3-20k --students 20000 --batch-students 1000 --row-group-rows 4096 --seed 20261029
3. Rodar testes Python: pytest -q tests/test_genesis_v3.py tests/test_sentinel_temporal_gate.py
4. Rodar testes Rails: bundle exec rails test test/services/analytics/student_query_service_test.rb
5. Disponibilizar DuckDB CLI como binário duckdb no PATH, ou configurar EPA_DUCKDB_CLI.

O serviço Analytics::StudentQueryService.call recebe student_id e dataset_version; sua agregação considera todo o histórico, não apenas N1/N2/N3. Não utilizar sua saída diretamente como feature de treinamento sem um novo filtro point-in-time.

## Restrições e aceites pendentes

- CI deve executar PyArrow real para validar comportamento Parquet; no ambiente de construção só foi possível validar compilação e mocks.
- Verificar a DuckDB CLI real em Windows e Linux, inclusive saída JSON.
- Medir RAM e tempo nas escalas 2k, 5k, 10k e 20k.
- Criar adaptador do MAPA ao schema v3 e conectar o SENTINEL ao gate de pré-treino.
- O SENTINEL atual desta mudança executa uma validação em memória para o contrato v2. Em escala, substituir por verificações DuckDB e anti-joins; exigir verificação criptográfica dos artefatos antes de emitir autorização.
- Definir registro de verificação imutável para evitar recalcular SHA-256 do Parquet a cada consulta.
- Criar controller e views para listar alunos e consultar históricos individuais paginados.
- Não interpretar correlação legítima entre notas passadas e desempenho futuro como vazamento: vazamento é dependência de informação indisponível no instante de previsão.
- Registrar a decisão negativa no SENTINEL e conservar o hash original no LEDGER; nunca adulterar o arquivo para "invalidar o hash".
