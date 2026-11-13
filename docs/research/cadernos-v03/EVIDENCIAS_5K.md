# Registro de evidências do benchmark sintético MAPA 5K

Referência técnica dos cadernos C01–C10, não substitui o JSON primário do experimento.

- **Data de consolidação:** 12/11/2026.
- **Schema:** `epa.mapa.statistical_evaluation.v1`.
- **Status:** `SYNTHETIC_NOT_EMPIRICALLY_VALIDATED`.
- **Manifesto das features:** SHA-256 `ec863d9f267564e27adf1a701f88951cf064af744eb2452708f120c22d947f23`.
- **Relatório JSON 5K:** SHA-256 informado no registro de congelamento `903298722b6b44cd9f955ee4ece73419781c3933deea27f1393ad84846f37836` (reverificar contra os mesmos bytes do arquivo primário).
- **Unidade independente para split/bootstrap:** estudante.
- **Selecionados:** 5.000; **treino/teste:** 3.750/1.250 estudantes; **observações por corte/seed:** 202.500/67.500.
- **Seeds de holdout:** 20261029, 20261030, 20261031.
- **Modelos no avaliador final:** `logistic_regression`, `mlp`.
- **Cutoffs:** N1, N2 e N3.
- **Bootstrap:** percentílico, 200 repetições agrupadas por estudante; comparação pareada com os mesmos grupos amostrados.
- **Tempo total:** 445,2471287 segundos medidos por `Measure-Command` no PowerShell; sem pico de RSS registrado.

| Corte | Modelo | Acurácia média | Macro-F1 médio | Recall reprovado médio | Log loss médio | Fit médio (s) |
|---|---|---:|---:|---:|---:|---:|
| N1 | Logística | 0,8259 | 0,7540 | 0,5025 | 0,3912 | 2,44 |
| N1 | MLP | 0,8291 | 0,7578 | 0,5099 | 0,3827 | 32,10 |
| N2 | Logística | 0,8772 | 0,8294 | 0,6671 | 0,2794 | 1,65 |
| N2 | MLP | 0,8767 | 0,8268 | 0,6518 | 0,2774 | 30,18 |
| N3 | Logística | 0,9224 | 0,8934 | 0,8033 | 0,1759 | 1,89 |
| N3 | MLP | 0,9217 | 0,8933 | 0,8266 | 0,1769 | 31,14 |

**Conclusão restrita:** melhora temporal dentro do gerador sintético; não há vencedor consistente entre MLP e Regressão Logística e não há validação em alunos reais. Os resultados de 500 e 2.000 estudantes aparecem em relatórios experimentais anteriores, mas seus JSONs não foram integrados a este PR; evitar misturar esses resultados como se fossem evidência primária do 5K.