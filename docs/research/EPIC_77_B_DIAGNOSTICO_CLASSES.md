# EPIC #77 — diagnóstico por classe no protocolo B (sem duplicar avaliador)

O módulo existente `epa.core_engine.mapa_protocol_runner` ganhou somente uma opção de **relatório**: `--class-metrics`. Por padrão, a saída JSON permanece com o contrato v1 anterior. Ativada a opção, o mesmo treinamento, seed e splits retornam também `class_order`, `class_support`, `recall_by_class` e `confusion_matrix` por modelo/fold. As matrizes usam linhas = classes reais e colunas = classes previstas, ordenadas por `CLASSES = (approved, recovery, failed)`.

## Executar no Windows PowerShell, depois do merge

```powershell
git switch develop
git pull origin develop
python -m pytest -q tests/test_mapa_protocol_runner.py
python -m epa.core_engine.mapa_protocol_runner \`
  --dataset "D:\\EPA-Experimentos\\genesis-epic77-v2" \`
  --protocol B_out_of_time \`
  --test-year 2026 \`
  --folds 3 \`
  --seed 20261029 \`
  --class-metrics \`
  --report "D:\\EPA-Experimentos\\resultados-epic77\\auditoria_classes_B.json"
```

**Atenção:** `--folds 3` no protocolo temporal B é somente parâmetro de interface; o planejador retorna **um único** holdout 2026. Conforme contrato existente, só entram no treino os anos 2020–2024 com rótulos disponíveis antes de 2026. O mesmo aluno pode aparecer no treino histórico e no teste futuro; esta execução **não** constitui teste de nova coorte C.

## Controle obrigatório antes da interpretação

Comparar `dataset_manifest_sha256`, `train_indices_sha256`, `test_indices_sha256`, `model_scores[].accuracy` e `model_scores[].f1_macro` com `protocolo_B.json` **para cada N1/N2/N3 e cada modelo**. Se qualquer valor divergir, não incluir recall/matriz no manifesto de evidências sem investigação.

As métricas por classe são resultados sintéticos; não inferir acurácia populacional, nem modificar valores congelados de P0/B. Os novos campos são uma extensão opt-in da saída, não um novo experimento de hiperparâmetros. Não colocar históricos de ALN1/ALN2 em arquivos ou PRs públicos.
