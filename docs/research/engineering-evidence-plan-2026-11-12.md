# EPA — Registro de engenharia e agenda de evidências (2026-11-12)

## Objetivo
Manter o laboratório local em Docker Compose e evoluir o GENESIS Rust com **equivalência de dados antes da otimização**. Preservar a tarefa central do TGI II: classificação de três classes (approved, recovery, failed) com análise complementar do risco (recovery+failed). Os resultados disponíveis são **exclusivamente sintéticos**.

## Evidências de referência recebidas do laboratório Windows
- GENESIS v2 com 120 estudantes/seed 20261029: 42 turmas, 840 matrículas, 324 ofertas e 25.920 registros bimestrais; manifesta hashes por arquivo.
- GENESIS v3 no mesmo catálogo/seed/quantidade: comparador Parquet (EXCEPT ALL) reportou PASS nas cinco entidades; 5,707 segundos foram registrados em uma execução local da v3 (medida isolada, não benchmark formal).
- MAPA: GroupKFold por estudante, 3 folds, cortes N1/N2/N3, modelos majoritário / regressão logística / Random Forest; resultados devem ser auditados antes de inclusão confirmatória no artigo.
- Condição temporal: GENESIS v2 reutiliza estudantes entre anos; avaliação de generalização para coorte futura independente não identificável.

## Contratos desta etapa Rust
- `generate-jsonl`: emite exatamente uma linha JSON por entidade/registro. **Não** produz Parquet nem realiza inferência. Piloto limitado a 2.000 alunos.
- Reutiliza a seed SHA-256 e o MT19937 portado de Python; notas, frequência e ausências seguem as mesmas fórmulas da `epa.genesis.v3.student_rows`.
- `tools/check_genesis_rust_stream.py`: compara cada registro Rust diretamente com a referência Python; a comparação utiliza tolerância absoluta explícita para valores de ponto flutuante e comparação exata para demais campos.
- Se o teste de paridade falhar, **não** usar o Rust para produzir datasets experimentais do MAPA até investigar cada diferença.
- Streams e APIs podem diferir em representação de ponto flutuante; aproximação numérica não é identidade de bytes/sha256 lógico.
- Dados existentes em `data/` não são alterados.

## Próximas tarefas de implementação
1. **Paridade matemática:** validar seeds diversas, bordas de arredondamento, classe/série, extremos de frequência, execução Windows/Linux. Registrar diferenças numéricas ULP e adequar o contrato.
2. **Persistência nativa:** produzir Parquet incremental e manifesto imutável em Rust, com escrita atômica, contagem/hash por entidade e validação referencial. Evitar comparações injustas de JSONL contra Parquet.
3. **Benchmark de engenharia:** comparar v2 Python/DuckDB, v3 Python/PyArrow e Rust/Parquet; múltiplas rodadas, warm-up, mesmo catálogo, hardware, tamanho, seed, ambiente, throughput, pico RSS, CPU, compressão, tempo da escrita e validade.
4. **Consultas e ingestão:** mapear SQL, N+1 e queries repetitivas nas rotas Rails, DuckDB e leitura Parquet; usar EXPLAIN/ANALYZE e perfis, índices e projeção colunar. O `executemany` v2 é candidato observado, **não diagnóstico por profiling ainda**.
5. **Auditoria científica:** contrato de features, prevenção de leakage, dados ausentes, desbalanceamento, fold agrupado por aluno, holdout temporal independente e análise de erros por classe. Separar exploração da confirmação.
6. **Modelos exploratórios:** inventariar implementações realmente presentes antes de testar; reportar baseline majoritário, LogisticRegression e RF como núcleo confirmatório; candidatos extras e testes de ablação ficam no laboratório exploratório.
7. **Estratégia de distribuição:** monólito modular Rails + workers Python/Rust via Docker Compose local. Sem Kubernetes ou VPS neste ciclo.

## Entregáveis documentais previstos (relatório integral, sem limite artificial)
- Inventário e maturidade de componentes ATLAS, GENESIS, MAPA, SENTINEL, LUPA, LEDGER e serviços adjacentes.
- Caderno matemático: equações completas de geração, pseudoaleatoriedade, distribuições, correlações, classificação, métricas, confiabilidade e intervalos.
- Arquitetura/stack: contexto, containers Docker, contratos de integração, interfaces e observabilidade.
- MER/DER: entidades, chaves, cardinalidades, integridade, versões e histórico de alterações.
- Casos de uso e cenários reais/sintéticos separados; fluxos de laboratório, coordenação, interpretação e intervenção.
- Estratégias algorítmicas e trade-offs: Python/DuckDB, Python/PyArrow, Rust, NumPy/Numba, Go/C++, custo computacional, portabilidade e manutenção.
- Consultas SQL, profiling e propostas fundamentadas de otimização, incluindo resultados negativos.
- Protocolos de testes e benchmarks, tabelas completas, matrizes de confusão, hashes, seeds, commit SHA e limitações de validade externa.
- Registro de decisões arquiteturais (ADR) e recomendações de evolução; artigo de 15–16 páginas será seleção do relatório, não substituto.

**Regra de evidência:** distinguir implementado, testado, inferido, proposto e não identificado. Não atribuir resultados a execuções ainda não realizadas.

## Auditoria de consultas — mapa de gargalos (etapa inicial)

### Evidência de código — preparação MAPA
- Antes: `student_timeline.build_snapshots` percorria novamente todos os registros disponíveis do mesmo estudante/disciplina ao criar cada snapshot; custo de varredura repetida proporcional ao número de anos observados.
- Nesta implementação: indexação única por `(student_id, subject_id)` e `enrollment_id`, processamento cronológico com acumulador de notas e frequências, mantendo exatamente os atributos e cortes anteriores.
- Teste de regressão: comparação contra cópia do algoritmo original com seeds diferentes, 1/7/24 estudantes, N1/N2/N3; a equivalência ainda depende de passar na CI.
- Não reportar speedup antes de comparar tempos e memória em execuções equivalentes. A etapa reduz repetição de varreduras, mas outras fases (geração, Parquet, validação, modelos) podem dominar o tempo total.

### Consultas e ingestão para inspeção posterior
- O projeto Rails atual usa **SQLite**, conforme `config/database.yml`; não assumir PostgreSQL em produção.
- No GENESIS v2, `duckdb.executemany` insere linhas individualmente — candidato a gargalo; requer profiling por entidade e comparação com Arrow/Parquet v3.
- `read_verified_v2` executa `SELECT * FROM read_parquet(?)` e materializa todas as tabelas em listas Python; avaliar projeção de colunas, filtragem, streaming e verificação de integridade sem perder invariantes.
- Monitorar contagem de consultas Rails, eager loading versus N+1, filtros e índices usando SQL logs e `EXPLAIN QUERY PLAN` do SQLite.
- Documentar consultas observadas com parâmetros anonimizados, tamanho da base, plano de execução, duração, volume lido e resultado da otimização.
