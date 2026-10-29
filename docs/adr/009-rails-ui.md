# ADR-009 — Interface Rails + Hotwire navegável

- Status: implementado como protótipo de navegação.
- Opção aceita: interface server-rendered, Rails 8 + importmap + Turbo, sem SPA React e sem frontend acoplado ao treinamento.
- Rotas: /, /datasets, /experiments, /models, /integrity, /architecture.
- Dataset: consulta apenas o manifesto sintético local de caminho fixo, exibindo metadados declarados, sem afirmar verificação.
- Experimento: formulário valida modelo/seed e apenas prepara instrução CLI; não executa subprocessos, não inicia treinamento nem produz métricas fictícias.
- Segurança: Rails CSRF no POST, nenhuma autenticação, RBAC, filas ou autorização de publicação ainda. Não disponibilizar publicamente com dados reais.
- Futuro: execução assíncrona controlada, estado de jobs, MLflow, auditoria Sentinel/Ledger, ingestão BNCC verificada.
