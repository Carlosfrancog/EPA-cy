# MAPA — Adaptador experimental das quatro notas bimestrais

**Status:** experimento exploratório, dados reais mantidos fora do repositório.
**Relacionamento:** epic #77, benchmark N4 #75 e calibração residual #76.

## Problema identificado

A calibração `mapa_n4_calibration.py` reconhecia o nome da disciplina apenas pela tabela de aliases do Ensino Médio, com acentos, e classificava entradas pré-2020 não reconhecidas como `OUTROS`. No corpus privado de referência, as grafias `matematica`, `ciencias`, `historia`, `portugues`, `ingles` e variantes de `educacao fisica` necessitam de mapeamento próprio. A versão experimental corrige o mapeamento por **área do conhecimento** sem equiparar Ciências do Fundamental diretamente a Biologia, Física ou Química do Médio. O módulo original não é alterado, para preservar a comparação histórica.

## Escopo da nova implementação

O adaptador de quatro bimestres toma como base o GENESIS v3, gera as mesmas notas sintéticas originais e ajusta **N1, N2, N3 e N4 em conjunto**. O ajuste conserva a sequência temporal sintética do próprio estudante/ano/disciplina e transforma sua média e amplitude de variação bimestral de acordo com estatísticas do histórico **2011–2019**. Por segurança, utiliza peso `0.4 × n/(n+20)`, deslocamento de média limitado a ±1,5 e escala intranual limitada a `[0.70, 1.45]`. Nenhum desses valores deve ser selecionado inspecionando os 36 gabaritos reais já avaliados.

**Não é o gerador GENESIS v4 definitivo.** O adaptador altera exemplos de treino (incluindo features e alvos), mas não reconfigura a geração multi-ano completa, frequência, faltas, nem o processo real de intervenções escolares. Ele preserva a variação multi-ano previamente sintetizada, sem alegar que aprendeu tendências populacionais do histórico de uma pessoa. A construção de uma nova versão integral do gerador exige um protocolo e variáveis reais adicionais.

## Procedimento de execução

```powershell
python -m pytest -q tests/test_mapa_n4_longitudinal.py
python -m epa.core_engine.mapa_n4_longitudinal `
  --catalog examples/atlas.demo.json `
  --inputs C:\EduPredict-Privado\entradas_n4_ensino_medio.csv `
  --calibration-history C:\EduPredict-Privado\historico_calibracao_2011_2019.csv `
  --answer-key C:\EduPredict-Privado\gabarito_n4_ensino_medio_PRIVADO.csv `
  --students 250 --seed 20261029 `
  --report C:\EduPredict-Privado\resultado_n4_longitudinal_v1.json `
  --predictions C:\EduPredict-Privado\previsoes_n4_longitudinal_v1.csv
```

Os dois arquivos de saída devem não existir anteriormente. Não adicionar esses arquivos, históricos reais, PKLs nem gabarito ao Git. Um único estudante produz observações correlacionadas; métricas por disciplina (três casos) são apenas descritivas.

## Diagnóstico que antecede a implementação

1. O diagnóstico original dos ajustes vazios em Matemática e Natureza é **falha de mapeamento de disciplina**; não é exclusão por suporte mínimo.
2. O cotejo sintético-versus-real deve usar média, dispersão, diferenças entre notas consecutivas, proporção de mudanças elevadas e suporte por área, com uma análise de sensibilidade separada para etapas Fundamental e Médio; não interpretar o contraste como equivalência de populações.
3. Reportar erros agregados por disciplina, série e magnitude da mudança N3→N4, sem ranquear modelos por acaso em testes já utilizados para elaboração da hipótese.

## Validade científica

- Treino apenas com casos sintéticos, estatísticas do histórico pré-2020 na adaptação; **gabarito 2020–2022 só é lido após os dois treinamentos**.
- A validade externa não é estabelecida; não há inferência causal sobre a pandemia.
- Métricas da rodada anterior (N4 original, residual) não são substituídas.
- Uma nova validação independente exigirá outros estudantes, períodos não examinados, ou ambas as condições.
- A comparação reprodutível com o **catálogo oficial** deve ser feita no ambiente privado do pesquisador; execuções reconstruídas em ambiente separado são preliminares.