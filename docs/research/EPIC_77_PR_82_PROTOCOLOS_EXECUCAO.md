# EPIC #77 — execução dos protocolos A/B/C para o MAPA sintético

Esta implementação **opt-in** não modifica os avaliadores, o GENESIS nem os relatórios N4 publicados.

## Contrato temporal

Tarefa: classificação do **desfecho final do mesmo ano** (`approved/recovery/failed`) com atributos N1/N2/N3. O gabarito só existe depois do quarto bimestre; por conservadorismo, representamos `label_available_year = academic_year + 1` e exigimos `label_available_year < test_year` nos treinos temporais. Isso cria uma defasagem de um ano escolar completo entre o ano observado e o ano-alvo de teste. É uma aproximação conservadora, não uma data real de publicação do boletim.

## Protocolos

- **A_grouped:** treina e testa em estudantes disjuntos, misturando anos; não mede desempenho em períodos futuros.
- **B_out_of_time:** treina somente em registros mais antigos com rótulo disponível e testa um ano posterior. Pode repetir estudantes entre os períodos, portanto **não mede generalização a novos alunos**.
- **C_unseen_future:** exige ano futuro e estudantes que não apareceram em **nenhum ano anterior** do conjunto observado, mesmo se o rótulo antigo não puder ser usado no treino. Se o dataset não contiver coorte nova, reporta `not_identifiable`.

Os relatórios contêm somente métricas agregadas sintéticas, SHA-256 do manifesto de origem e digests de índices. Não trazem identificadores individuais.

## Execução

Crie um dataset GENESIS v2 local com `python -m epa.genesis.v2 --catalog examples/atlas.demo.json --students 40 --seed 20261029 --start-year 2020 --output <DIRETORIO>` (confira os flags do comando `--help`). Depois:

```bash
python -m pytest -q tests/test_mapa_validation_protocols.py tests/test_mapa_protocol_runner.py
python -m epa.core_engine.mapa_protocol_runner --dataset <DIRETORIO> --protocol A_grouped --folds 3 --report <SAIDA_A.json>
python -m epa.core_engine.mapa_protocol_runner --dataset <DIRETORIO> --protocol B_out_of_time --test-year 2026 --report <SAIDA_B.json>
python -m epa.core_engine.mapa_protocol_runner --dataset <DIRETORIO> --protocol C_unseen_future --test-year 2026 --report <SAIDA_C.json>
```

**Aviso:** o dataset GENESIS v2 atual repete os estudantes entre anos, então C deve retornar `not_identifiable`, não uma métrica inventada. O B fornece uma avaliação temporal sintética limitada, não validação em escolas reais.

Próximos PRs: seleção aninhada de hiperparâmetros sem consulta ao teste e manifesto final imutável de congelamento. A EPIC #77 inclui também infraestrutura P2, fora do congelamento offline.