# ADR-005 — Estados, imutabilidade e quarentena

- Status: Aceito como direção; ainda sem enforcement
- Estados pretendidos: CREATED → STAGED → VALIDATED → RESEARCH_APPROVED → PUBLISHED. Falhas: QUARANTINED ou REJECTED.
- Decisão: conteúdo aprovado é imutável; revisão de artefato em quarentena requer nova versão e trilha de decisão. Assinaturas do publicador serão separadas das identidades dos workers.
- Observação: hash isolado não atesta procedência. O mecanismo de publicação e as atestações criptográficas ainda não foram desenvolvidos.
