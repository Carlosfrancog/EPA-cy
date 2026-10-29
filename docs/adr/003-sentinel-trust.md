# ADR-003 — EPA Sentinel, segurança progressiva e validade científica

- Status: Aceito como direção; implementação parcial
- Decisão: o Sentinel controla ingresso de dados, execução científica, checagem temporal, integridade, decisões de política e bloqueio de publicação. Zonas Raw, Validated, Research e Published com classificação independente (Synthetic/Public/Restricted/Personal).
- Política: falha crítica implica quarentena; evidência insuficiente não autoriza publicar. Dados pessoais reais excluídos do MVP até análise de privacidade e autorização específica.
- Limite atual: `epa.sentinel.policy` verifica somente digests e dependências declaradas; **não** valida assinaturas, origem externa, isolamento real de workers nem proveniência completa.
- Verificação futura: simulações de adulteração, vazamento e testes comparativos contra baseline.
