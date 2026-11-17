# EPIC #77 — auditoria incremental e portas de congelamento científico

**Escopo auditado:** `develop`, em 17/11/2026. Esta matriz descreve **implementações identificadas** e pendências de **integração específica**, não uma certificação de produção. Fonte de requisitos: [issue #77](https://github.com/Carlosfrancog/EPA-cy/issues/77).

## 1. Três tarefas e universos de evidência **não equivalentes**

| Linha | Alvo | Dados | Protocolo/estado |
|---|---|---|---|
| CORE ENGINE legado (`experiment.py`) | aprovação média no ano seguinte >= 6 (binário) | GENESIS sintético | `GroupShuffleSplit`, pipeline; **não é N4** |
| MAPA N1/N2/N3 (`mapa.py`, `mapa_research.py`, `mapa_statistical_evaluator.py`) | `approved/recovery/failed` (três classes) | sintético com cortes por bimestre | grouped CV e avaliador estatístico existem em componentes distintos |
| MAPA N4 (`mapa_real_n4.py`, `mapa_n4_calibration.py`, `mapa_n4_longitudinal.py`, `mapa_n4_loso.py`) | nota numérica N4 (0–10) | treino sintético, avaliação retrospectiva de dois alunos reais | 36 resultados/estudante; **dois clusters humanos**, sem teste cego independente |

Não combinar F1 do classificador com MAE dos regressores. Resultados sintéticos não certificam eficácia em escolas; histórico acadêmico de dois alunos não certifica validade populacional.

## 2. Matriz de evidências da EPIC #77

| Requisito | Situação constatada | Evidência / lacuna exata |
|---|---|---|
| P0 — grupos estudantes disjuntos | **Implementado em componentes** | `experiment.py`, `mapa.py`, `mapa_native_training.py`: `GroupShuffleSplit`; `mapa_research.py`: `GroupKFold` |
| P0 — CV agrupado | **Implementado em MAPA Research** | `mapa_research.py::evaluate_protocol` e `mapa_research_extended.py::evaluate`; não é um contrato único para todas as tarefas |
| P0 — avaliação temporal | **Parcial** | `mapa_research.py` marca `same_students_across_years` como não identificável **para coorte futura independente**; ainda falta protocolo separado para período futuro permitindo mesmos IDs com bloqueio temporal |
| P0 — data de disponibilidade do alvo | **Lacuna transversal** | corte temporal baseado apenas no ano da observação pode confundir disponibilidade do rótulo; o novo `mapa_validation_protocols.py` exige `label_available_year` explícito |
| P0 — pré-processamento por fold | **Implementado nas pipelines inspecionadas** | `mapa.py` e `experiment.py` usam imputação/escala dentro do `Pipeline`; extensões exigem testes próprios |
| P1 — estabilidade de sementes | **Implementado parcialmente** | `mapa_statistical_evaluator.py` agrega múltiplas sementes em população sintética fixada; não é garantia em todas as rotas |
| P1 — incerteza por cluster | **Implementado parcialmente** | `mapa_uncertainty.py`, `mapa_statistical_evaluator.py`; intervalos condicionais à população sintética e modelo ajustado |
| P1 — probabilidades e calibração | **Implementado parcialmente** | `mapa_statistical_evaluator.py`: Brier, log-loss, ECE descritiva; não fazer calibração com teste |
| P1 — regularização/busca de hiperparâmetros | **Pendente como protocolo integrado** | modelos possuem alguns parâmetros fixos, mas falta seleção aninhada com validação separada e trilha de tentativas |
| P1 — ablação/feature importance | **Pendente como bateria transversal** | implementar sem consultar teste final e sem alegação causal |
| P1 — MLflow | **Disponível opcionalmente** | `mapa_tracking.py` para relatórios MAPA sintéticos; não equivale a registro universal dos experimentos |
| P1 — integridade e rastreabilidade | **Parcial** | manifests SHA-256 em exportação/treino; falta um manifesto **unificado por execução**, código e ambiente |
| P1 — privacidade dos dois alunos | **Isolamento manual documentado** | entradas, gabaritos e relatórios individuais permanecem fora do GitHub; formalizar política de retenção, acesso e descarte |
| P2 — workers, autenticação, UX, Ledger | **Não homologado nesta auditoria** | exige revisão específica dos componentes Rails e de infraestrutura; não alegar conclusão operacional |

### Correção conceitual para a issue

O comentário de que faltava `GroupKFold` ou MLflow deve se referir ao **benchmark legado** / à falta de integração transversal; estas capacidades já estão implementadas em módulos MAPA. Não marcar a EPIC inteira como concluída por isso.

## 3. Entrega P0 desta branch — somente planejador de splits

`epa/core_engine/mapa_validation_protocols.py` oferece três cortes exclusivamente sobre metadados **SYNTHETIC**, sem carregar gabaritos nem ajustar modelos:

- **A_grouped:** `GroupKFold`, estudante excluído entre treino e teste, sem alegar validade temporal.
- **B_out_of_time:** `academic_year < test_year` e **`label_available_year < test_year`** no treino; o mesmo estudante pode aparecer no futuro; mede deslocamento temporal, não identidades novas.
- **C_unseen_future:** os dois requisitos temporais acima e estudantes do teste ausentes no treino; se não existir nova coorte, `status=not_identifiable` (nunca inventar resultado).

A saída guarda índices, digests das listas de índices, contagens e anos. **Não executa modelos, não cria métricas e não é, por si só, um benchmark de validação temporal.** `label_available_year` deve ser estabelecido por contrato de dataset com disponibilidade real do alvo; não estimar silenciosamente. Os snapshots por disciplina podem compartilhar `student_id` e `academic_year`.

Testes incluem vazamento temporal, sobreposição por aluno, caso sem nova coorte, dataset não sintético e dados insuficientes.

## 4. Próximas entregas mínimas para congelar a bateria científica

1. **P0 integração temporal e auditoria de disponibilidade:** adapter explícito do contrato de rótulo em cada tarefa (classificação ano-seguinte versus N4), sem alterar scores anteriores. Validar A/B/C em coortes sintéticas independentes e em anos diferentes; reportar impossibilidade quando não identificável.
2. **P1 robustez/regularização aninhada:** seeds pré-registradas, test/validation separados por grupo ou ano, regularização com orçamento limitado, baselines fixos, desempenho treino-validação e controles de permutação de labels. Teste nunca seleciona parâmetros.
3. **P1 congelamento:** manifesto versionado por execução com git SHA, hash catálogo/dataset/script, dependências, flags, seeds, splits, tempo e métricas; artefatos imutáveis; tabela de lacunas e documentação de reprodução. Preservar resultados negativos.
4. **P2 operacional (trilha separada):** fila durável, isolamento de workers, autorização, observabilidade, Sentinel e Ledger não são pré-requisitos automáticos do *congelamento científico offline*, mas **continuam pendentes da EPIC** e impedem alegar homologação da plataforma completa.

## 5. Registro das evidências reais (fora do Git)

Manter os relatórios individuais N4, histórico real e manifestos privados **fora do checkout**, com hashes locais. Para N4 com os dois alunos, o melhor MAE médio de controle foi **0,861111** (persistência N3 e média N1–N3, empate); a Linear transferida ficou **0,886834**, e a Random Forest piorou (**0,912165 → 0,940744**). Todos os 72 alvos estão correlacionados por **2 estudantes humanos**, e ambos os conjuntos já foram inspecionados. Não usar esses alvos para escolher o vencedor do próximo ciclo nem para computar IC populacional.

Não publicar: PKLs, dados tabulares reais, predições individuais, gabaritos, nomes, matrículas, amostras anônimas pequenas reidentificáveis. Se for necessário compartilhar agregados, aplicar revisão de divulgação de pequeno N.

## 6. Condição de encerramento

A entrega atual marca **auditoria P0 iniciada**, não `EPIC DONE` nem `FROZEN`. Congelamento científico exige execução final reproduzível, versões e hashes verificados, um relatório explícito por protocolo e declaração dos limites. O artigo vem **depois** desse congelamento; eventual conclusão da EPIC de infraestrutura depende também das entregas P2.