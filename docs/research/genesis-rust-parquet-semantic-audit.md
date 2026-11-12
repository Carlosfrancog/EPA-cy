# GENESIS — Auditoria semântica SQL para datasets Rust grandes

## Objetivo

Complementar a integridade criptográfica dos manifests GENESIS com validação **semântica** de cinco Parquet gerados pelo motor Rust. O benchmark 5k/10k comprovou hashes e contagens de arquivos, mas não relacionamentos, domínios de notas/frequência, unicidade ou equivalência Python.

## Ferramenta

`python tools/audit_genesis_parquet.py --dataset data/rust-scale-<id>/dataset --output data/audit-genesis-10k.json`

É necessário usar o **diretório real** do dataset de 5k ou 10k, encontrado em `data/rust-scale-*/dataset`; não substituir o placeholder literalmente. Saída JSON é escrita em modo exclusivo (nunca sobrescreve arquivo existente). O código utiliza DuckDB diretamente sobre os Parquet, agregando resultados no SQL, sem carregar tabelas inteiras para listas Python. Parâmetros opcionais: `--memory-limit 512MB --threads 2`.

Checks de contagem/manifesto e SHA-256 por arquivo, unicidade de identificadores e chaves compostas, integridade referencial entre matrícula, estudante, turma e oferta, consistência de ano/série/área, domínio de notas [0,10], sessões, presenças, ausências justificadas e taxa de frequência derivada (arredondada a seis casas). Relata médias e intervalos de nota/frequência, número de alunos/disciplinas/anos distintos, distribuição por período e área do conhecimento.

Um check positivo (>0) gera `status=FAIL`; o CLI encerra com exit code 1 para facilitar CI. Inconsistência de manifesto/hash aborta com erro em vez de emitir PASS. Testes cobrem dataset mínimo íntegro, taxa de frequência inconsistentes mesmo com SHA correto e adulteração de arquivo.

## Operação sugerida

1. Fazer merge somente após CI verde e executar `python -m pytest -q tests/test_genesis_parquet_deep_audit.py`.
2. Apontar o auditor para a geração 5.000 estudantes existente; repetir para a de 10.000.
3. Enviar os relatórios JSON. Não prosseguir 25k/50k enquanto as consultas semânticas não passarem.
4. Executar novos datasets de 25k de forma incremental, registrando RSS, duração, espaço em disco e validação de agregados.

## Limites científicos e operacionais

- Isso não é comparação registro a registro com o Python, não valida distribuição populacional de estudantes reais e não mede qualidade de treinamento do MAPA.
- O SQL verifica vários relacionamentos e invariantes, mas não comprova automaticamente todas as regras da geração sintética; novos invariantes podem ser incorporados.
- `SET memory_limit` restringe alocações controladas pelo DuckDB, **não equivale a um teto de RSS do processo**. O Parquet ainda pode demandar espaço de disco para leitura temporária.
- A verificação de SHA percorre os arquivos sequencialmente e aumenta o tempo total de auditoria.
- Não há alteração do motor Rust, contratos de geração ou baseline MAPA neste PR.
