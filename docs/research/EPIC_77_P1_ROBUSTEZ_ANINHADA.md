# EPIC #77 — P1: regularização, controle de overfitting e estabilidade

**Status: metodologia implementada; resultados oficiais dependem de execução no checkout do EPA-cy.**

## Contexto e fronteira

A bateria P0 (protocolos A/B/C) gerou relatórios sintéticos com 40 estudantes GENESIS v2, três classificadores e cortes N1/N2/N3. O protocolo C não era identificável por não existir coorte futura de estudantes inéditos. Esta bateria P1 **não substitui** P0 nem altera os relatórios históricos ou os casos privados N4 de dois estudantes.

## Protocolo experimental

`epa.core_engine.mapa_robustness` lê somente um diretório GENESIS v2 verificado, rejeita registros não classificados como `SYNTHETIC` e processa N1/N2/N3 separadamente. Para cada corte e seed:

1. **Teste externo intocado**: `GroupShuffleSplit` por `student_id` (25%) e hash dos índices. Mesmo aluno nunca aparece nos dois conjuntos nesta execução.
2. **Seleção interna**: `GroupKFold(n_splits=3)` aplicado **somente ao treino externo**, independente do teste. Parâmetros fixados antes da execução: Regressão Logística `C ∈ {0.1, 1, 10}` e Random Forest `min_samples_leaf ∈ {1, 4, 8}`, 100 árvores, profundidade máxima 12. Dummy majoritário sem hiperparâmetros.
3. Melhor candidato selecionado pelo **F1-macro médio de validação interna**, com desempate por ordem pré-fixada. Não usar resultados externos para decidir configurações.
4. Refit no treino externo completo e calcular F1-macro/accuracy **no treino e teste**. Guardar o gap treino–teste apenas como diagnóstico, não prova automática de overfitting.
5. Controle negativo: embaralhar somente os rótulos do treino externo, reentreinar o mesmo candidato selecionado e avaliar nos rótulos externos intactos. Resultado anormal nesse controle **não equivale** a prova isolada de vazamento.
6. Repetir com as seeds pré-fixadas `20261029`, `20261030`, `20261031`. Reportar médias e desvio-padrão (descritivos, **não** intervalos de confiança de generalização).

**Atenção:** esta é uma avaliação agrupada por estudante e **não é um teste out-of-time**. A bateria P0/B cobre o cenário temporal separadamente. Um eventual efeito benéfico de uma configuração não deve ser selecionado olhando o N4 dos alunos reais.

## Execução no Windows

```powershell
cd D:\EPA-cy\EPA-cy
python -m pytest -q tests/test_mapa_robustness.py
python -m epa.core_engine.mapa_robustness `
  --dataset 'D:\EPA-Experimentos\genesis-epic77-v2' `
  --seeds 20261029 20261030 20261031 `
  --inner-folds 3 `
  --report 'D:\EPA-Experimentos\resultados-epic77\robustez_P1_v1.json'
```

O arquivo de saída é imutável por caminho; escolha outro nome para replicações. Com mais registros sintéticos ou mais árvores, o tempo de treinamento aumenta. Não publicar arquivos pessoais nem gabaritos; este experimento não precisa deles.

## Portas para congelamento

- CI do código completo e saída do novo CLI com hash do manifest original.
- Revisar classe rara, desbalanceamento, F1-macro e gap por seed/corte.
- Não selecionar seed/modelo para o artigo pelo teste final.
- Auditoria dos warnings (incluindo ausência de valores históricos e convergência) deve diferenciar avisos explicáveis de falhas impeditivas.
- Congelamento científico em manifesto distinto com commit, versões do ambiente e SHA-256 dos relatórios; artefatos reais individuais permanecem privados.
- Não declarar toda a EPIC #77 encerrada enquanto os itens de segurança/infraestrutura P2 não forem implementados ou formalmente separados do escopo científico.