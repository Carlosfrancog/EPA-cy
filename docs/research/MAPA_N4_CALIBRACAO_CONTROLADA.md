# MAPA N4 — Calibração temporal exploratória, etapa 2

## Contexto e objetivo

Comparar **duas condições** sobre os mesmos 36 casos retrospectivos (um estudante real, 2020–2022): **GENESIS v3 original, sem calibração** e **GENESIS v3 original + sobreposição de calibração do alvo N4**. A segunda condição NÃO altera o código, as distribuições geradas ou os IDs do GENESIS; modifica apenas os *rótulos sintéticos de treino* segundo um deslocamento residual estimado nos anos **2011–2019**. Chamar essa técnica de *adaptação sintética por residual* é mais preciso do que alegar que o gerador inteiro foi recalibrado.

### Fronteira temporal, vazamento e desenho

- Calibração privada: registros reais de 2011–2019 (Fundamental) com N1–N4, apenas para estimar **diferença média N4 − média(N1,N2,N3)**. O arquivo de calibração deve ser gerado localmente; **nenhum arquivo real é versionado**.
- Avaliação privada: 36 N4 de 2020, 2021 e 2022 (Ensino Médio). **Não entram no ajuste dos resíduos, geração, escolha de parâmetros ou fit**.
- Ambos os cenários usam os mesmos estudantes sintéticos GENESIS, entradas N1–N3, catálogo versionado, seed e regressores. Somente o vetor de alvos sintéticos sofre o ajuste pré-fixado.
- Offset com encolhimento por área (`AREA_SHRINK=20`), referência global quando não existem registros suficientes, intensidade fixa `0,5`; predições limitadas a `[0,10]`. **Não ajustar constantes para maximizar a pontuação real.**
- Baselines N3 e média N1–N3 devem permanecer idênticas nas duas condições e são controle de integridade.
- Diferença entre etapas (Fundamental → Médio), composição curricular, uma única trajetória e seleção já informada pelos resultados anteriores: **não permite alegar generalização, causalidade, validação prospectiva ou ganho robusto**. O resultado é exploratório; novos estudantes serão necessários para validação externa.

## Execução (PowerShell), com dados fora do repositório

Depois do merge da branch, ou usando a branch local de desenvolvimento:

```powershell
python -m pip install -e ".[dev,research]"
python -m pytest -q tests/test_mapa_n4_calibration.py

# Etapa privada: PKL de autoria do pesquisador, sabidamente confiáveis.
python scripts/export_n4_calibration_private.py `
  --pkl-zip "C:\EduPredict-Privado\historico_pkl_corrigido.zip" `
  --output "C:\EduPredict-Privado\historico_calibracao_2011_2019.csv"

python -m epa.core_engine.mapa_n4_calibration `
  --catalog "examples/atlas.demo.json" `
  --inputs "C:\EduPredict-Privado\entradas_n4_ensino_medio.csv" `
  --calibration-history "C:\EduPredict-Privado\historico_calibracao_2011_2019.csv" `
  --answer-key "C:\EduPredict-Privado\gabarito_n4_ensino_medio_PRIVADO.csv" `
  --students 250 --seed 20261029 `
  --report "C:\EduPredict-Privado\resultado_n4_calibrado_v1.json" `
  --predictions "C:\EduPredict-Privado\previsoes_n4_calibradas_v1.csv"
```

O CLI rejeita a sobrescrita dos relatórios. O `.json` contém médias agregadas, hash SHA-256 do catálogo e do CSV privado de calibração, configuração fixa, modelos e diferenças `MAE_calibrado − MAE_original`. O `.csv` individual com previsões fica **privado**. A ausência de gabarito gera apenas previsões, sem métricas.

## Critério de aceitação e integridade

1. Arquivos reais e perfis de calibração ficam **fora do Git** e de workflows públicos.
2. Se houver qualquer registro de 2020–2022 no CSV de calibração, a execução falha.
3. Sem N4 e MF nas features de treino ou predição.
4. Dados sintéticos preservados; mesmas features, seeds e modelos nas duas condições.
5. Testes unitários e CI; comparar referência original ao benchmark N4 congelado, observando versões de dependência.
6. Não reportar como descoberta de melhoria populacional nem usar os 36 alvos para nova otimização.

## Continuação científica

Avaliar robustez a diferentes sementes e a tamanhos de população sintética **sem escolha por resultado N4**, e mais adiante obter validação com novos estudantes não utilizados no desenho. Esta etapa não cobre ajuste de distribuições de N1–N3, causalidade de pandemia nem intervenção pedagógica.