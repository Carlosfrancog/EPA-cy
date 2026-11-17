# MAPA N4 — diagnóstico privado de transferência entre dois estudantes

**Status:** exploratório, não validação populacional. Vinculado à EPIC #77.

## Escopo mínimo

O código executa duas transferências: calibra a distribuição sintética usando somente o histórico pré-2020 de ALN1 e avalia N4/2020–2022 de ALN2; depois inverte ALN2 → ALN1. Os modelos permanecem treinados exclusivamente no GENESIS sintético. Portanto **não** é validação leave-one-student-out de pesos de modelos treinados em dados reais: é isolamento por estudante dos **parâmetros de calibração**. Também calcula a condição original não calibrada nos mesmos 36 casos de cada estudante. Os dados já foram examinados em análises exploratórias; isso não cria um conjunto de teste independente.

Normalização central aceita acentos, caixa, espaços, `_` e `-` em nomes reconhecidos; não faz correspondência difusa de matérias. `Ciências` no Fundamental não é tratada como disciplina específica do Ensino Médio. O adaptador histórico existente continua usando seu mapeamento explícito por área.

## Configuração local

Arquivos CSV originais e o manifesto JSON **não devem ser versionados no Git**. Crie `C:\EduPredict-Privado\dois_alunos.json` com caminhos reais (ajuste os nomes conforme seu disco):

```json
{
  "students": [
    {"student":"ALN1","inputs":"C:\\EduPredict-Privado\\entradas_n4_ensino_medio.csv","calibration_history":"C:\\EduPredict-Privado\\historico_calibracao_2011_2019.csv","answer_key":"C:\\EduPredict-Privado\\gabarito_n4_ensino_medio_PRIVADO.csv"},
    {"student":"ALN2","inputs":"C:\\EduPredict-Privado\\ALN2\\entradas_n4_ensino_medio_ALN2.csv","calibration_history":"C:\\EduPredict-Privado\\ALN2\\historico_calibracao_2011_2019_ALN2_PRIVADO.csv","answer_key":"C:\\EduPredict-Privado\\ALN2\\gabarito_n4_ensino_medio_ALN2_PRIVADO.csv"}
  ]
}
```

```powershell
python -m pytest -q tests/test_mapa_n4_loso.py tests/test_mapa_real_n4.py tests/test_mapa_n4_longitudinal.py
python -m epa.core_engine.mapa_n4_loso `
  --manifest "C:\EduPredict-Privado\dois_alunos.json" `
  --catalog examples/atlas.demo.json `
  --students 250 --seed 20261029 `
  --report "C:\EduPredict-Privado\loso_n4_report.json" `
  --predictions "C:\EduPredict-Privado\loso_n4_predictions_PRIVADO.csv"
```

O relatório contém métricas agregadas por estudante pseudonimizado e SHA-256 da referência; o CSV opcional de previsões permanece privado. Não imprima nem envie notas pessoais para CI. Artefatos são imutáveis por padrão; use um nome novo para repetir a execução.

## Aceite e interpretação

- Exatamente dois perfis, com 36 casos cada; a N4 do avaliado só é aberta após o treino e as previsões.
- Mapeamento controlado e rejeição de disciplinas não reconhecidas.
- Comparação por estudante, inclusive direção da transferência, além de média de MAE **com peso igual por estudante** (não contar as 72 notas como 72 estudantes independentes).
- Testes automatizados não contêm dados reais.
- Não escolher hiperparâmetros a partir das 72 N4 reais; congelar posteriormente sementes, protocolo, hashes e resultados na EPIC #77 antes de redigir o artigo.