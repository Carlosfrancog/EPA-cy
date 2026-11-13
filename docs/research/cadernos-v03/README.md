# EduPredict Analytics — Cadernos Científicos C01–C10

**Versão 0.3 · TGI II · 12 nov. 2026**

Documentos de apoio ao artigo científico, construídos a partir do **benchmark sintético final do MAPA com 5.000 estudantes**. Os dez cadernos e o glossário possuem versão **Markdown editável** e **PDF A4 com apresentação acadêmica inspirada nos documentos SBC v0.2 do projeto** (fonte serifada, título central, resumos, seções numeradas, referências, legendas, cabeçalho e rodapé). Os PDFs não substituem o template oficial de submissão da SBC — a adequação editorial do artigo final continua necessária.

## Índice

| Caderno | Assunto | Documento PDF |
|---|---|---|
| C01 | Problema de pesquisa, classes e hipóteses | [C01](pdfs/C01_EPA_SBC.pdf) |
| C02 | GENESIS Rust e proveniência longitudinal | [C02](pdfs/C02_EPA_SBC.pdf) |
| C03 | MAPA temporal e prevenção de vazamento | [C03](pdfs/C03_EPA_SBC.pdf) |
| C04 | Particionamento, métricas e baselines | [C04](pdfs/C04_EPA_SBC.pdf) |
| C05 | Modelos, MLP e Random Forest | [C05](pdfs/C05_EPA_SBC.pdf) |
| C06 | Bootstrap por estudante e incerteza | [C06](pdfs/C06_EPA_SBC.pdf) |
| C07 | Calibração, log loss e Brier | [C07](pdfs/C07_EPA_SBC.pdf) |
| C08 | Resultados sintéticos e erros | [C08](pdfs/C08_EPA_SBC.pdf) |
| C09 | Custo, escalabilidade e reprodutibilidade | [C09](pdfs/C09_EPA_SBC.pdf) |
| C10 | Síntese científica, limites e escrita | [C10](pdfs/C10_EPA_SBC.pdf) |

**Glossário:** [Markdown](fontes/GLOSSARIO.md) · [PDF](pdfs/GLOSSARIO_EPA_SBC.pdf). **Figuras:** [`figuras/`](figuras/), com identificadores e legendas nos cadernos.

## Evidências do 5K

- Contrato `epa.mapa.statistical_evaluation.v1`, status `SYNTHETIC_NOT_EMPIRICALLY_VALIDATED`.
- Manifesto de features SHA-256 `ec863d9f267564e27adf1a701f88951cf064af744eb2452708f120c22d947f23`.
- População única GENESIS; seleção 5.000 estudantes, treino 3.750 e teste 1.250 por holdout.
- Seeds `20261029`, `20261030`, `20261031`; três cortes N1, N2, N3; Regressão Logística e MLP.
- 200 reamostragens bootstrap agrupado por estudante para cada seed/corte.
- Tempo *wall clock* do PowerShell: **445,2471287 s**; pico de RSS **não medido**.
- As médias plotadas são descritivas: três holdouts **não representam três populações independentes**.
- O relatório 5K original deve ser arquivado externamente com seu hash na pasta de evidências do projeto para reprodução completa. O presente PR não inclui a base Parquet nem contém dados de estudantes reais.

## Regenerar PDFs

Na raiz do repositório, com Python 3.11+:

```powershell
python -m pip install reportlab matplotlib pillow pypdf
python docs/research/cadernos-v03/gerar_cadernos.py
```

As saídas são escritas em `docs/research/cadernos-v03/pdfs/` e gráficos em `figuras/`. A geração de gráficos utiliza as médias e intervalos 5K explicitamente congelados no próprio script; verifique contra o relatório original antes de alterar quaisquer valores. Os PDFs gerados em máquinas diferentes podem variar em metadados e na tipografia de fallback.

## Política editorial e integridade

1. Resultados numéricos do 5K são sintetizados do relatório técnico congelado; exemplos matemáticos são **didáticos**, não novas medições.
2. Os diagramas de rede MLP e floresta são **esquemáticos**; não representam pesos, thresholds, árvores ajustadas ou telemetria de épocas efetivamente exportada.
3. A variável prevista é o **resultado final da disciplina**, não evasão/abandono escolar.
4. Os intervalos bootstrap são condicionais aos estudantes e estimadores avaliados. Não estabelecer superioridade universal entre modelos, causalidade ou aplicabilidade empírica.
5. Antes de incorporação ao artigo v0.3, revisar citações/DOIs, métodos, ortografia, autoria, compatibilidade do template oficial SBC e integridade de valores contra as evidências primárias.