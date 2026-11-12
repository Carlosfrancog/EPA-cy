# EduPredict Analytics — continuidade de pesquisa e produto (05/11/2026)

> Registro de discussão para o TGI II. Este documento contém **propostas**, não comprova implementação, homologação ou disponibilidade de um modelo nacional. Preserva a diferença entre resultados históricos do TGI I e experimentos atuais do EPA.

## Decisões de produto em discussão

1. **Inferência com modelo pré-treinado:** a instituição importa dados escolares e usa uma versão distribuída, sem precisar treinar na própria escola. A eventual atualização da release ocorre em ciclo de pesquisa controlado.
2. **Modelos especializados por ano escolar:** investigar predição do **2º ano do Ensino Médio** com histórico até o 1º e do **3º ano** com histórico até o 2º. Comparar modelos especializados com um modelo mais geral. Definir se o alvo é classificação final (aprovado/recuperação/reprovado), notas por disciplina, ou ambos em tarefas distintas.
3. **Não confundir protocolos:** M1/M2/M3 do TGI I antecipavam resultados dentro do próprio ano após N1/N2/N3; predição longitudinal do ano seguinte é uma tarefa de ML diferente e precisa de protocolo, dados e avaliação próprios.
4. **Demonstração de banca:** usar preferencialmente **um XLSX com abas** para estudante, matrículas, anos, disciplinas, avaliações e faltas. Uma interface importa o histórico, seleciona ano-alvo/release, executa **somente inferência**, apresenta o previsto e, depois, permite revelar/importar o desempenho real do ano previsto para comparação.
5. **Proteção contra leakage:** dados do ano previsto não entram nas features daquele teste. O aluno/coorte da demonstração, idealmente, fica fora de treino, seleção e ajuste da release usada. Registrar data de corte, versão e resultado original imutável.
6. **Feedback e evolução:** resultados reais posteriormente registrados podem ser candidatos a uma base de futuros treinamentos, após validação. **Não há autoaprendizado, retreinamento nem promoção automática.** Avaliar pesos por ano-alvo somente como hipótese experimental com ablação e holdout.
7. **Distribuição:** estudar pacote versionado com ONNX para inferência interoperável (se a conversão/paridade funcionar), skops para Python, pré-processamento, schema/ordem de features, classes, metadados, métricas auditadas, hashes, dependências, exemplos, licença e model card. MLflow serve ao rastreamento científico; não substitui a homologação.
8. **Escalabilidade futura:** modelo-base e eventual adaptação regional/institucional somente com avaliação própria. Dados sintéticos não sustentam alegação de prontidão para escolas reais no Brasil.

## Issues de planejamento já existentes

| Issue | Conteúdo | Conexão |
| --- | --- | --- |
| [#8](https://github.com/Carlosfrancog/EPA-cy/issues/8) | EPA Neural Observatory / Forest Explorer 3D | Visualização exploratória posterior; não substitui a pesquisa quantitativa |
| [#9](https://github.com/Carlosfrancog/EPA-cy/issues/9) | Família evolutiva de modelos, momentos M1/M2/M3, versões e champion/challenger | Arquitetura central para novos modelos e distribuição |
| [#10](https://github.com/Carlosfrancog/EPA-cy/issues/10) | GENESIS v2, histórico longitudinal por estudante, período, disciplina, turma e presença/faltas | Fonte estrutural para snapshots sem vazamento temporal |

## Issues abertas em 05/11/2026

| Issue | Discussão |
| --- | --- |
| [#37](https://github.com/Carlosfrancog/EPA-cy/issues/37) | Modelos longitudinais especializados por ano escolar (2º e 3º EM) |
| [#38](https://github.com/Carlosfrancog/EPA-cy/issues/38) | Demo: importar XLSX, executar inferência por ano e comparar com desempenho real |
| [#39](https://github.com/Carlosfrancog/EPA-cy/issues/39) | Pacote completo de modelos estáveis: ONNX/skops + metadados, dependências e testes |
| [#40](https://github.com/Carlosfrancog/EPA-cy/issues/40) | Feedback de resultados observados e retreinamento controlado por versão |
| [#41](https://github.com/Carlosfrancog/EPA-cy/issues/41) | Auditoria de inconsistência entre matriz histórica M3 e acurácia declarada de 94% |

## Desenvolvimento já documentado em PRs do repositório

* **#11–#14:** GENESIS v2, Student Timeline point-in-time, MAPA N1/N2/N3 e laboratório Rails.
* **#15–#19:** MLflow opcional, vínculo de runs, avaliação e validação cruzada por estudante/coortes.
* **#20–#24:** LUPA (explicabilidade), diagnóstico, critérios de evidência e incerteza via bootstrap.
* **#25–#29:** variantes MLP/XGBoost e protocolos comparativos de pesquisa.
* **#30–#33:** observatório interativo 3D LUPA e auditorias locais de integridade.
* **#34–#36:** observabilidade, smoke/homologação experimental e GENESIS v3 streaming + DuckDB + SENTINEL.

As descrições desses PRs **não são por si sós prova de merge em branches específicas nem validação externa**. Conferir estado dos merges e CI antes de alegar funcionalidade entregue. O laboratório atual reporta resultados sintéticos, não avaliação homologada em escolas brasileiras.

## Auditoria prioritária antes de qualquer release estável

O documento histórico TGI I publica uma matriz de confusão do M3 com diagonal **1284 + 342 + 267 = 1893 acertos** sobre **2300 casos**, equivalente a **82,30%**, enquanto outras tabelas relatam **94,0%** de acurácia. Também há diferença entre 2300 observações dessa matriz e a quantidade esperada em uma divisão simples 80/20 da base declarada de 15.613 registros. É obrigatório rastrear as execuções e confirmar se são experimentos diferentes ou erro de documentação. Não corrigir números por hipótese.

## Priorização sugerida

1. **P0 — #41:** rastreabilidade científica e reconciliação dos números históricos.
2. **P1 — #10 e #37:** contrato de históricos/snapshots e modelo longitudinal efetivamente treinado e avaliado.
3. **P1 — #38:** interface de demonstração com XLSX, inferência pré-treinada e comparação retrospectiva.
4. **P2 — #39 e #40:** distribuição auditável, versionamento, feedback e política de atualização.
5. **P3 — #8:** visualização 3D e refinamentos de UX.

## Perguntas ainda abertas para retomada

* Qual saída é prioritária: **classificação anual**, **notas por disciplina**, ou ambas?
* Qual o layout dos históricos realmente disponíveis? Como tratar mudanças curriculares, transferência, repetência e anos ausentes?
* Qual estudante/coorte ficará inteiramente fora do treinamento e da seleção para a demonstração?
* ONNX será compatível com o pipeline completo? Haverá paridade de previsão e probabilidade com o estimador original?
* Quais métricas e limites de desempenho mínimos viabilizam uma versão para pesquisa, sem alegar uso operacional?

## Uso no artigo

Criar/refinar seção de desenvolvimento sobre **versionamento, persistência e distribuição dos modelos** e seção de método sobre **predição longitudinal e avaliação retrospectiva** somente quando existirem implementações e evidências verificáveis. Separar claramente *implementado*, *avaliado em dados sintéticos*, *planejado* e *validado externamente*. O estudo com o resultado real revelado depois da predição pode compor um estudo de caso, sem induzir conclusão de generalização a partir de um único estudante.
