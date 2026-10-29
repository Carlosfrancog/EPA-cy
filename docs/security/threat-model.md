# Modelo inicial de ameaças — EPA Sentinel

## Ativos e limites

Ativos: dados sintéticos, dados pessoais futuros, currículos versionados, manifestos, features, modelos, métricas, evidências e chaves de assinatura.

Fronteiras: entrada de fontes → Raw; Raw → Validated; Validated → worker Research; resultados → staging; staging → Published. Um digest válido não é autorização de publicação.

## Ameaças prioritárias

| ID | Ameaça | Tratamento previsto |
| --- | --- | --- |
| T01 | Adulteração de conteúdo e manifesto | Digest + atestação assinada (assinatura pendente) |
| T02 | Feature indisponível no momento de predição | Dependências temporais verificadas |
| T03 | Sobreposição de estudante entre partições quando proibida | Teste protocolado de isolamento |
| T04 | Fit do pré-processamento com teste | Pipeline e testes de separação |
| T05 | Worker comprometido / acesso indevido | Container e permissões mínimas (pendente) |
| T06 | Artefatos Python não confiáveis | Evitar desserialização insegura e verificar origem |
| T07 | Vazamento via logs/métricas | Redação, classificação e publicação controlada (pendente) |
| T08 | Manipulação de auditoria | Registro verificável e append-only (pendente) |
| T09 | Seleção oportunista de resultados | Protocolos pré-registrados e teste reservado |

## Propriedades e limites

A versão inicial somente avalia digest e timestamps de dependências **autodeclaradas**. Não use como garantia contra manifestos maliciosos. Não execute dados pessoais reais sob este MVP. Não exponha a CLI como serviço de rede sem isolamento. Trate `UNKNOWN` como falha de autorização.
