# ADR-006 — EPA Ledger: cadeia local de evidências

- **Status:** Aceito como direção, implementação experimental.
- **Problema:** resultados precisam ser ligados a artefatos, políticas e decisões auditáveis sem expor dados escolares brutos.
- **Decisão:** representar eventos de auditoria em JSONL com serialização determinística, contador sequencial, SHA-256 do evento e vínculo ao hash do evento anterior. Identificar o assunto pelo SHA-256 do conteúdo, não por nome de estudante.
- **Fronteira:** o processo gravador deve ter permissão restrita. A primeira versão não autoriza concorrência de escritores.
- **Falha:** histórico inválido deve interromper a gravação e a verificação. Ausência de histórico significa ausência de evidência, não aprovação.
- **Limites:** um invasor com acesso à escrita completa pode recalcular a cadeia, remover um sufixo, apagar o arquivo ou alterar o relógio. Portanto, cadeia consistente **não implica autenticidade, completude ou imutabilidade**.
- **Evolução:** checkpoints assinados e ancorados externamente; gerenciamento de chaves, armazenamento restrito, controle de versões de esquemas, verificação de identidade e retenção.
- **Aceitação inicial:** testes de detecção de alteração, truncamento e quebra de encadeamento.
