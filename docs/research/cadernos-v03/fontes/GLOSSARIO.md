# Glossário técnico cumulativo — EduPredict Analytics

**Acurácia:** proporção de todas as observações corretamente classificadas. Não garante bom desempenho em classes raras.

**Baseline:** modelo simples de referência, por exemplo, prever sempre a classe majoritária.

**Balanced accuracy:** média do recall de cada classe; evita que classes muito frequentes dominem o resumo.

**Bootstrap:** reamostragem com reposição usada para caracterizar variabilidade de estatísticas sob suposições explícitas.

**Bootstrap por cluster:** sorteia grupos inteiros correlacionados; no EPA, estudantes e todos seus registros de teste.

**Brier multiclasse:** média da soma dos quadrados da diferença entre probabilidades previstas e indicadores das classes reais. Menor = melhor.

**Calibração:** correspondência entre probabilidade prevista e frequência observada em conjuntos comparáveis.

**Classe minoritária:** classe que ocorre menos frequentemente, como reprovação neste conjunto sintético.

**Data leakage:** uso indevido de informação futura, do alvo ou do conjunto de teste em preparação, ajuste ou seleção.

**ECE (Expected Calibration Error):** desvio médio ponderado por faixas de probabilidade; sensível ao binning e às frequências das classes.

**Feature (atributo):** variável de entrada, como frequência observada até o corte.

**Falso negativo (FN):** observação da classe de interesse classificada como outra classe; reprovação não detectada é exemplo relevante.

**Falso positivo (FP):** observação apontada como da classe de interesse mas pertencente a outra classe.

**Fit time:** tempo de ajuste do algoritmo, excluindo leitura, transformações e análise posterior, se medido assim.

**F1-score:** média harmônica entre precisão e recall para uma classe: 2PR/(P+R).

**Holdout:** subconjunto reservado para avaliar o modelo fora do ajuste.

**Hiperparâmetro:** configuração fixada antes do ajuste, como número de neurônios.

**IC 95%:** intervalo produzido por método estatístico cuja interpretação depende do modelo de amostragem; não fornece probabilidade frequentista do parâmetro fixo.

**Log loss:** penalidade probabilística logarítmica que pune confiança alta em respostas erradas.

**Macro-F1:** média aritmética dos F1 das classes, concedendo o mesmo peso a cada classe; útil sob desbalanceamento.

**Manifesto:** arquivo que descreve identidade, esquema, proveniência e artefatos de um dataset.

**MLP (Multilayer Perceptron):** rede neural de camadas densas para aprender relações não lineares entre atributos e classes.

**One-vs-rest:** avaliação da classe especificada contra a união de todas as outras.

**Parquet:** armazenamento colunar eficiente para processamento analítico.

**Point-in-time:** restrição temporal que permite somente dados conhecidos no momento da predição.

**População sintética:** dados gerados programaticamente; não substituem amostras escolares observadas.

**Precisão (precision):** TP/(TP+FP), fração dos alertas positivos que estavam corretos.

**Recall (sensibilidade):** TP/(TP+FN), fração de casos verdadeiros da classe que o modelo recuperou. Recall 50% de reprovação significa que cerca de metade das observações realmente reprovadas foi detectada.

**Reliability diagram:** visualização de probabilidades médias previstas versus frequência empírica do evento por faixas.

**RSS (Resident Set Size):** memória física residente em processo, diferente da memória virtual reservada.

**Seed:** valor inicial que torna reproduzíveis sorteios pseudoaleatórios num dado ambiente.

**SHA-256:** hash criptográfico usado para identificar os bytes do manifesto; não prova validade científica dos dados.

**Snapshot temporal:** visão dos atributos no momento de corte N1, N2 ou N3.

**Split agrupado:** separação de treino e teste por identificador de estudante, evitando linhas do mesmo aluno em ambos.

**Suporte (support):** número de observações reais pertencentes a determinada classe.

**Target (alvo):** variável que o classificador tenta prever, neste caso desfecho final da disciplina.

**Trade-off:** compromisso entre objetivos, como antecipação do alerta e precisão da identificação.

**Wall time:** duração real de todo o comando, incluindo carregamento, ajuste, avaliação e gravação.