# ADR-004 — Workers locais isolados, arquitetura distribuível

- Status: Aceito como direção; não implementado
- Decisão: workers Python com permissões mínimas, containers locais no MVP, saída de artefatos por staging e contrato de tarefa versionado.
- Pendências: identidade do worker, política de recursos, transporte de mensagens, autenticação mútua, restrições de rede, armazenamento de secrets, recuperação de falhas e idempotência.
- Verificação: worker não pode ler diretórios alheios nem publicar diretamente.
