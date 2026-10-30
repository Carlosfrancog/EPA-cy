# ADR-010 — EPA Laboratory v0: execução pela UI

Data: 2026-10-29
Status: implementação experimental

## Decisão

- Persistir runs em SQLite operacional com estados `queued`, `running`, `completed`, `failed`, `quarantined`.
- Para desenvolvimento local, usar ActiveJob `async` no Rails. O adapter é **volátil**; reinícios podem deixar jobs incompletos.
- O POST só é aceito em desenvolvimento/teste e quando a origem da requisição é local; sem autenticação e worker durável, **não liberar execução pública**.
- O Python é chamado com `Open3.capture3` e argv fixo, nunca shell montado com entradas web.
- Dataset sintético padrão: `data/demo/academic_history.parquet`; caso ausente, Genesis gera 500 estudantes com seed fixa.
- O benchmark completo executa três baselines; `model_key` define apenas qual deles recebe destaque na interface.
- Armazenar relatório JSON, digests e status no Rails; nenhuma métrica de demonstração é confundida com desempenho real.
- Relatórios aparecem somente após JSON do Core Engine validado.
- Não declarar EPA Ledger e Sentinel integrados; esta versão aplica apenas verificação de digest no Core Engine e controle de origem no Rails.

## Riscos ainda abertos

- `async` não fornece garantias de processamento confiável ou fila distribuída.
- `Timeout.timeout` não é garantia de término de processos filhos; requer supervisão/containers com hard limits antes da produção.
- Geração concorrente da demo pode causar colisões; um job pode falhar e não será reprocessado automaticamente.
- Não há autenticação, autorização de usuários, quotas, MLflow, checkpoints assinados ou retenção.
- Persistência operacional em SQLite fica limitada a experimentos locais e volumes modestos.
- Não usar dados pessoais reais, nem disponibilizar execução ao público.

## Critérios de aceite

- Integração Rails: valida entrada e enfileira uma vez.
- Job: transições auditáveis e deduplicação por claim atômico.
- Relatórios: provenientes de Python e com schema, métricas e digests verificados.
- UI: seis páginas navegáveis e detalhe com status e métricas reais.
- CI: testes de Rails/Python e capturas de screenshots de execução local.
