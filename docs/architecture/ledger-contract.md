# EPA Ledger v0 — Contrato de auditoria

## Evento

Campos obrigatórios: `schema_version`, `sequence`, `event_type`, `subject_digest`, `recorded_at`, `payload`, `previous_hash`, `event_hash`.

`event_hash = SHA256(canonical_json(event_without_event_hash))`.

`previous_hash` aponta ao evento anterior; no primeiro evento, é composto por 64 zeros. O arquivo usa linhas JSON UTF-8 terminadas em newline.

O digest do assunto **deve ser conhecido por origem independente** para que a verificação tenha valor de integridade.

## API Python

- `append_event(path, event_type, subject_digest, payload, recorded_at)`
- `read_verified(path)`
- `verify_subject(path, expected_digest)`

`append_event` requer exclusividade de escritor garantida pelo chamador. A implementação local não é segura para writers concorrentes nem para filesystem não confiável.

## Segurança não implementada

- assinaturas, chaves e identidade de atestadores;
- imutabilidade comprovável ou checkpoint externo;
- garantia de relógio;
- controles de confidencialidade para payload;
- sistema de autorização e retenção;
- publicação confiável e mecanismos contra reescrita completa;
- integração com MLflow, Rails, worker containers ou Parquet.

Nunca enviar dados pessoais, notas individuais ou secrets para `payload` nesta fase.
