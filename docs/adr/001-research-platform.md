# ADR-001 — Plataforma científica em monorepo

- Status: Aceito
- Contexto: TGI II requer experimentos reproduzíveis, não um ERP escolar.
- Decisão: Rails + Hotwire para experiência web e orquestração; Python para pesquisa; módulos EPA ATLAS, GENESIS, CORE ENGINE, SENTINEL e LEDGER no mesmo repositório.
- Consequências: menos CRUD e interfaces; contratos explícitos entre Rails e Python; sem arquitetura de microsserviços obrigatória.
- Verificação: um experimento completo com entrada, resultado e evidências reproduzíveis.
