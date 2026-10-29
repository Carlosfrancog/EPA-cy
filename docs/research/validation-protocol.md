# Protocolo de validação — proposta inicial

Hipótese: verificação de proveniência + admissibilidade temporal detecta violações que verificações triviais de nomes de features podem perder, com custo mensurável.

Baselines: B0 (controle mínimo), B1 (verificações convencionais bem implementadas), E1 (mecanismos EPA Sentinel).

Campanhas: V1 leakage temporal, V2 contaminação de grupos/partições e pré-processamento, V3 adulteração de artefatos, V4 isolamento dos workers, V5 reprodutibilidade e custo.

Métricas: recall e precisão da detecção, falso positivo, false-negative, latência de verificação, impacto em CPU/memória e completude de proveniência.

Regras científicas: snapshots M1/M2/M3 não podem incluir notas futuras; fitted transformers usam apenas treino; separação de estudantes depende da hipótese de generalização; resultados sintéticos não são validação empírica em alunos reais.

A função `verify_manifest` é somente um primeiro teste de unidade. Não implementa as campanhas nem uma prova de segurança.
