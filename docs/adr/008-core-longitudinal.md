# ADR-008 — EPA Core Engine v0: baseline longitudinal

- Status: experimento inicial, não modelo validado.
- O Genesis produz observações sintéticas por estudante, ano e disciplina; o Core define um alvo independente: média das notas do **ano seguinte** >= 6, usando somente atributos observados até o ano de origem.
- Este alvo NÃO equivale a evasão, nem à classificação M1/M2/M3 do TGI I. Os protocolos serão comparados futuramente sem misturar métricas.
- Primeiro benchmark: DummyClassifier, LogisticRegression e RandomForest; split GroupShuffleSplit por estudante, sem identidade compartilhada entre treino/teste.
- Imputação e normalização realizadas após separação, dentro do Pipeline scikit-learn.
- Features: média e frequência atual, média histórica e inclinação acumulada, anos observados, médias das quatro áreas do conhecimento; não inclui alvo futuro.
- Dados de entrada Parquet com manifesto SHA-256 verificado; saída JSON não sobrescrevível.
- Limites: **não há validação temporal out-of-time, tuning, cross-validation, registro no MLflow, inferência em produção nem auditoria completa de provenance**; o gerador é artificial.
- Sucesso inicial: testes de integridade, isolamento e comparabilidade das três abordagens; não pressupor acurácia alta.
