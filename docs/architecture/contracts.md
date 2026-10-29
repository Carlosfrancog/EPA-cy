# Contratos e fronteiras

## Contrato inicial de manifesto

Campos obrigatórios: `schema_version`, `classification`, `artifact_path`, `digest_algorithm`, `digest`, `prediction_at`, `dependencies[]` com `feature` e `available_at` em ISO 8601 com timezone.

Retorno: `PERMIT`, `DENY` ou `UNKNOWN`, com motivos. **PERMIT só confirma verificações declaradas no MVP; não autoriza publicação.**

## Evolução contratual

- `TaskRequest`: task_id, experiment_id, dataset_version, protocol_digest, identity, inputs, constraints, idempotency_key.
- `TaskResult`: task_id, status, artifact_digest, provenance_ref, errors.
- `Attestation`: identidade verificada, chave, algoritmo, digest do sujeito, cadeia de dependências.
- `PublicationDecision`: decisões de revisão, política e justificativas auditáveis.

## Zonas

Raw → Validated → Research → Published. Quarantined é estado de bloqueio, não zona de confiabilidade. Classificação de dados é independente da zona.
