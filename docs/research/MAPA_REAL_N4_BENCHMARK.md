# MAPA — Retrospectiva de N4 (pesquisa exploratória)

**Status:** `REAL_RETROSPECTIVE_SINGLE_STUDENT`; dados reais **não versionados**.

## Hipótese e procedimento

O objetivo é ocultar N4 e qualquer média final (MF) em 36 casos de uma única trajetória escolar de 2020 a 2022 (12 disciplinas × três séries, com notas reais autorizadas) e prever N4 a partir de N1, N2 e N3. O alvo só é lido depois do ajuste dos modelos, para aferição do erro.

O treinamento inicial usa **exclusivamente o gerador original, não calibrado** `epa.genesis.v3.student_rows` com o catálogo `examples/atlas.demo.json`; não usa os dados de 2011–2022 no ajuste, e não usa nenhuma N4 real para otimização. São distintos do MAPA de classificação já congelado: estes algoritmos estimam **nota numérica**.

**Limitação importante:** todos os 36 casos são de **um estudante**, portanto não há 36 amostras humanas independentes. Nenhum resultado indica generalização para estudantes, redes ou escolas. Dado que os mesmos valores do histórico foram inspecionados durante o desenho do experimento, este é um **ensaio retrospectivo exploratório**, não um estudo cego prospectivo.

## Entradas e integridade

O avaliador lê CSV privado apenas com estas colunas: `id_caso,serie,ano_letivo,disciplina,N1,N2,N3`. A presença de N4, MF ou colunas inesperadas causa erro. O gabarito fica em outro arquivo, contendo `id_caso,N4_real,MF_real`, do qual somente `N4_real` é consumido **após o treinamento**. O loader rejeita contagens diferentes de 36, identificadores duplicados e notas fora de `[0,10]`.

O treino é gerado em memória pelos **mesmos parâmetros e PRNG** do GENESIS v3 original; nenhuma população é calibrada com resultados reais. O catálogo inclui dez disciplinas na etapa do Ensino Médio e não contém Inglês (`ING`) ou Educação Física (`EDF`), que são avaliadas via atributos de área e categoria não vista; essa extrapolação deve ser analisada separadamente. Nenhuma frequência real está disponível no CSV; logo, **não usar o conjunto de 11 features com frequência** do classificador MAPA de outra tarefa.

## Algoritmos

- Referências: persistência de N3, média simples N1–N3, preditor de média sintética.
- Regressão Linear, Ridge, Random Forest, Extra Trees, Gradient Boosting, Histogram Gradient Boosting e MLP Regressor.
- As versões classificatórias (`LogisticRegression`, `RandomForestClassifier`, `MLPClassifier`) **não** são empregadas para prever notas numéricas; a tarefa exige regressores.
- Parâmetros congelados (250 árvores RF/ExtraTrees, até 450 iterações MLP com early stopping e 200 estimadores Boosting) **sem escolher configuração a partir de N4 real**.

## Como executar localmente

Instale as dependências declaradas em `pyproject.toml`:

```bash
python -m pip install -e '.[dev,research]'
python -m pytest -q tests/test_mapa_real_n4.py
```

Mantenha os CSVs **fora do repositório**. Exemplo Linux/macOS (ajuste paths):

```bash
python -m epa.core_engine.mapa_real_n4 \
  --catalog examples/atlas.demo.json \
  --inputs /dados-privados/entradas_n4_ensino_medio.csv \
  --answer-key /dados-privados/gabarito_n4_ensino_medio_PRIVADO.csv \
  --students 250 --seed 20261029 \
  --report /dados-privados/resultados_mapa_n4.json \
  --predictions /dados-privados/previsoes_n4.csv
```

Os relatórios locais incluem apenas métricas agregadas e contagem de casos; o CSV de previsões contém os identificadores dos casos e permanece privado. **Não execute o comando com saída dentro do repositório, não faça commit de dados reais ou relatórios por caso.**

## Métricas e critérios de interpretação

Aferir MAE, RMSE, mediana do erro absoluto, proporção dentro de ±0,5 e ±1,0 ponto. Comparar erros por disciplina e série em ambiente privado. Reportar custo de ajuste, `seed`, hash do catálogo sintético e semântica da regressão.

Os regressores não são necessariamente superiores aos métodos ingênuos; o resultado deve preservar todos os métodos e não escolher vencedores olhando o teste, nem repetir retreinos até obter melhora neste único caso real. A calibração posterior do GENESIS exige desenho novo, conjunto de avaliação distinto e pré-registro: não contaminar este controle original.

## Execução local de verificação, 15 nov. 2026

Uma execução exploratória **fora do GitHub** foi feita com código de geração localmente transcrito da função `student_rows` do GENESIS v3 (requer repetição com o módulo e o JSON exatos do repositório para conclusão final). Foram 250 estudantes sintéticos, 7.500 pares sintéticos de disciplina/ano, 36 notas observadas de um estudante e dez abordagens incluindo as duas baselines. Os arquivos de resultados reais individuais e o catálogo reproduzido localmente **não são publicados**. O ensaio não calibrou GENESIS. A execução oficial no próprio repositório é parte da verificação do PR.