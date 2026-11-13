#!/usr/bin/env python3
"""Reproduz 10 cadernos técnicos SBC-like do EPA a partir de Markdown auditável.
Requer: reportlab, matplotlib, pypdf. Sem dados de produção.
"""
from pathlib import Path
import re, json, math, statistics, html, hashlib, textwrap
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, PageBreak, HRFlowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from xml.sax.saxutils import escape

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/'fontes'; PDF=ROOT/'pdfs'; FIG=ROOT/'figuras'
for p in [SOURCE,PDF,FIG]:p.mkdir(exist_ok=True,parents=True)
DATA={
 'N1': {'logistica':{'f1':.7540,'acc':.8259,'failed':.5025,'loss':.3912,'brier':.2450,'fit':2.44}, 'mlp':{'f1':.7578,'acc':.8291,'failed':.5099,'loss':.3827,'brier':.2401,'fit':32.10}},
 'N2': {'logistica':{'f1':.8294,'acc':.8772,'failed':.6671,'loss':.2794,'brier':.1745,'fit':1.65}, 'mlp':{'f1':.8268,'acc':.8767,'failed':.6518,'loss':.2774,'brier':.1738,'fit':30.18}},
 'N3': {'logistica':{'f1':.8934,'acc':.9224,'failed':.8033,'loss':.1759,'brier':.1097,'fit':1.89}, 'mlp':{'f1':.8933,'acc':.9217,'failed':.8266,'loss':.1769,'brier':.1106,'fit':31.14}}
}
PAIRS=[('N1',20261029,-.00112,-.00347,.00158),('N1',20261030,-.00036,-.00279,.00314),('N1',20261031,-.01003,-.01349,-.00689),('N2',20261029,.00228,.00060,.00415),('N2',20261030,.00449,.00215,.00678),('N2',20261031,.00104,-.00120,.00328),('N3',20261029,.00087,-.00077,.00247),('N3',20261030,.00098,-.00102,.00294),('N3',20261031,-.00132,-.00296,.00025)]
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.right':False,'axes.spines.top':False,'savefig.facecolor':'white'})
C1='#195d5b';C2='#b67838'

def plot_metric(metric, ylabel, out):
 fig,ax=plt.subplots(figsize=(9.2,3.0));xs=[1,2,3]
 for model,label,color in [('logistica','Regressão Logística',C1),('mlp','MLP',C2)]:
  vals=[DATA[f'N{x}'][model][metric] for x in xs]
  if metric in ('acc','failed'):vals=[v*100 for v in vals]
  ax.plot(xs,vals,'o-',linewidth=2,markersize=6,label=label,color=color)
 ax.set_xticks(xs,['N1','N2','N3']);ax.set_ylabel(ylabel);ax.grid(axis='y',alpha=.25);ax.legend(frameon=False,ncol=2,loc='best');fig.tight_layout();fig.savefig(FIG/out,dpi=170);plt.close(fig)
plot_metric('f1','Macro-F1 médio (0 a 1)','macro_f1.png')
plot_metric('failed','Recall reprovação (%)','recall_reprovacao.png')
plot_metric('fit','Tempo médio de ajuste (s)','tempos_fit.png')
plot_metric('loss','Log loss (menor = melhor)','log_loss.png')
fig,ax=plt.subplots(figsize=(9.3,4.0));ys=range(9)
for i,(cut,seed,delta,lo,hi) in enumerate(PAIRS):
 ax.plot([lo,hi],[i,i],lw=3,color=C2 if lo>0 or hi<0 else C1)
 ax.plot(delta,i,'o',color='black',ms=4)
ax.axvline(0,color='gray',lw=1,ls='--');ax.set_yticks(list(ys),[f'{c} · {str(s)[-2:]}' for c,s,*_ in PAIRS]);ax.invert_yaxis();ax.set_xlabel('Δ macro-F1 = Logística − MLP (intervalo bootstrap 95%)');ax.grid(axis='x',alpha=.2);fig.tight_layout();fig.savefig(FIG/'pareados.png',dpi=170);plt.close(fig)

# Diagramas explicitamente conceituais, desenhados de forma vetorial pelo matplotlib.
def diagram(nodes,edges,file):
 fig,ax=plt.subplots(figsize=(9.0,2.7));pos={k:(x,y) for k,x,y in nodes};
 for a,b in edges:
  x,y=pos[a];xx,yy=pos[b];ax.annotate('',xy=(xx-.25,yy),xytext=(x+.25,y),arrowprops={'arrowstyle':'->','lw':1.4,'color':'#668f8a'})
 for name,(x,y) in pos.items():
  ax.text(x,y,name,ha='center',va='center',fontsize=9,wrap=True,bbox={'boxstyle':'round,pad=.45','fc':'#eaf5f1','ec':C1,'lw':1.2})
 ax.set_xlim(-.6,9.6);ax.set_ylim(-.45,2.9);ax.axis('off');fig.tight_layout();fig.savefig(FIG/file,dpi=170);plt.close(fig)
diagram([('GENESIS',.7,1.5),('Parquet temporal',3.4,1.5),('MAPA N1/N2/N3',6.4,1.5),('Relatórios JSON',8.9,1.5)], [('GENESIS','Parquet temporal'),('Parquet temporal','MAPA N1/N2/N3'),('MAPA N1/N2/N3','Relatórios JSON')],'arquitetura.png')
diagram([('Anos anteriores',.8,1.5),('N1',3.1,1.5),('N2',5.6,1.5),('N3',8.3,1.5)], [('Anos anteriores','N1'),('N1','N2'),('N2','N3')],'linha_tempo.png')
diagram([('IDs estudantes',1.0,1.5),('Split agrupado',3.8,1.5),('Treino 75%',6.6,2.35),('Teste 25%',6.6,.65)], [('IDs estudantes','Split agrupado'),('Split agrupado','Treino 75%'),('Split agrupado','Teste 25%')],'split.png')
fig,ax=plt.subplots(figsize=(9.0,3.25));layers=[(0,11),(2.3,32),(4.6,16),(6.9,3)]
for i,(x,n) in enumerate(layers):
 ys=[(j+.5)/n*2.9 for j in range(n)]
 for j,y in enumerate(ys):
  if i<3:
   nextn=layers[i+1][1]; ty=(int(j*nextn/n)+.5)/nextn*2.9
   ax.plot([x+.09,layers[i+1][0]-.09],[y,ty],c='#b7d4cd',lw=.7,zorder=1)
  ax.add_patch(plt.Circle((x,y),.05 if n>16 else .075,facecolor=C1 if i!=3 else C2,edgecolor='white',lw=.2,zorder=2))
 ax.text(x,-.2,['11 atributos','32 ocultos','16 ocultos','3 classes'][i],ha='center',fontsize=9)
ax.set_xlim(-.5,7.5);ax.set_ylim(-.4,3.05);ax.axis('off');fig.tight_layout();fig.savefig(FIG/'mlp.png',dpi=170);plt.close(fig)
fig,ax=plt.subplots(figsize=(9,2.75));
for t in range(3):
 offset=t*3;nodes=[(1.0,2.0),(0.3,1.0),(1.7,1.0),(0.0,.1),(.6,.1),(1.4,.1),(2.0,.1)]
 for a,b in [(0,1),(0,2),(1,3),(1,4),(2,5),(2,6)]:
  x,y=nodes[a];xx,yy=nodes[b];ax.plot([x+offset,xx+offset],[y,yy],c=C1,lw=1.5)
 for x,y in nodes:ax.scatter([x+offset],[y],s=170,c=C2 if y==.1 else C1,zorder=3)
 ax.text(offset+1,2.4,f'Árvore {t+1} (esquema)',ha='center',fontsize=9)
ax.set_xlim(-.5,8.5);ax.set_ylim(-.25,2.65);ax.axis('off');fig.tight_layout();fig.savefig(FIG/'floresta.png',dpi=170);plt.close(fig)

FONTE='Fonte: elaboração própria, com base no relatório sintético MAPA 5K (schema epa.mapa.statistical_evaluation.v1).'
CHAPTERS={
'01':('Problema de pesquisa, escopo e hipóteses', 'Definir a tarefa supervisionada, a unidade observacional e os limites de inferência do EduPredict Analytics.', '''## 1. Contexto e motivação
A disponibilidade de notas, presenças e informações históricas não significa que uma escola possua um mecanismo validado de intervenção. O EduPredict Analytics (EPA) propõe uma infraestrutura de pesquisa que transforma registros acadêmicos em instantâneos temporais, compara algoritmos e conserva evidências verificáveis. O objetivo deste caderno é declarar o problema e seus limites antes de interpretar qualquer percentual de acerto.

A pergunta investigada nesta fase é: **em condições sintéticas controladas, qual desempenho classificatório é obtido para o resultado final da disciplina quando somente registros disponíveis até N1, N2 ou N3 são fornecidos?** A pergunta **não** é se o sistema prevê evasão escolar com confiabilidade real.

## 2. Tarefa e unidade de análise
A variável-alvo possui três classes mutuamente exclusivas: **aprovado**, **recuperação** e **reprovado**. Cada observação corresponde a um contexto de matrícula/ano e disciplina, avaliado em determinado corte. Um estudante pode, portanto, originar muitas observações; elas não constituem indivíduos estatísticos independentes.

O alvo é o desfecho da disciplina. Retenção escolar, evasão, transferência, abandono e permanência são fenômenos distintos que exigiriam rótulos e observações específicos. Utilizar o termo «risco de evasão» para essas predições seria uma extrapolação não sustentada.

## 3. Hipóteses operacionais
**H1 (antecedência):** ao avançar de N1 para N3, o modelo incorpora mais evidências e melhora a classificação no mesmo processo gerador sintético. **H2 (parcimônia):** um classificador linear pode atingir desempenho próximo ao de uma rede multicamadas. **H3 (robustez local):** o desempenho se mantém relativamente estável quando o subconjunto selecionado cresce de 500 para 5.000 estudantes, dentro da mesma população geradora.

Essas hipóteses são examinadas com **macro-F1**, acurácia, recall por classe, log loss, Brier e tempo de ajuste. A comparação de modelos usa separação agrupada por estudante e diferenças pareadas calculadas com as mesmas observações de teste.

## 4. Contribuição e fronteiras
O estudo combina engenharia de dados sintéticos, contratos temporais verificáveis, avaliação por cortes, estimadores e ferramentas de diagnóstico probabilístico. A contribuição científica é metodológica e computacional: **demonstração reprodutível dentro de um ambiente simulado**; não comprovação de eficácia operacional em uma escola.

## 5. Leitura preliminar do resultado
No teste 5K, o macro-F1 da Regressão Logística passou de 0,7540 (N1) para 0,8934 (N3). Para o MLP passou de 0,7578 a 0,8933. Os valores são médias descritivas de três holdouts sobre a mesma população sintética, não replicações populacionais independentes.

![macro_f1.png|Figura 1. Macro-F1 médio por corte.]

## 6. Vocabulário em formação
**Classificação multiclasse:** atribuição de uma entre três classes. **Alvo (target):** resultado a prever. **Feature:** atributo utilizado como entrada. **Holdout:** separação de dados para avaliar um modelo fora de sua amostra de ajuste. **Macro-F1:** média não ponderada do F1 das classes; evita privilegiar somente a classe abundante.

## 7. Síntese crítica
A viabilidade observada é limitada ao ecossistema sintético sob contrato. A conclusão do artigo deverá separar o que o sistema executou do que ainda depende de dados reais, estudo longitudinal independente e avaliação de utilidade pedagógica.'''),
'02':('GENESIS Rust e proveniência longitudinal','Explicar o papel do gerador sintético e a rastreabilidade necessária para reprodução sem confundir simulação com evidência empírica.', '''## 1. Finalidade do GENESIS
O GENESIS Rust produz registros sintéticos longitudinais para testar a infraestrutura quando o uso de dados acadêmicos reais ainda não está autorizado ou disponível. Os estudantes, matrículas, disciplinas e períodos são entidades de uma população simulada. O gerador permite testes de carga, consistência e validação de contratos; não estabelece que suas distribuições reproduzam automaticamente as de escolas brasileiras.

## 2. Caminho de proveniência
O fluxo analisado parte de dados GENESIS, passa por transformações temporais MAPA, produz Parquet por corte e termina em relatórios JSON versionados. O identificador do manifesto de features do benchmark 5K é **ec863d9f267564e27adf1a701f88951cf064af744eb2452708f120c22d947f23**. O SHA-256 registra identidade de conteúdo, não garante realismo estatístico, ausência de vieses ou integridade de todo o ambiente externo.

![arquitetura.png|Figura 1. Cadeia conceitual de proveniência entre gerador, atributos e evidências.]

## 3. Escala e significado dos registros
Na execução 5K foram escolhidos 5.000 estudantes da população sintética de origem. Cada divisão reuniu 3.750 estudantes no treino e 1.250 no teste; por corte e seed, 202.500 observações de treino e 67.500 de teste. O total de linhas é maior que o de estudantes por causa de disciplinas e anos letivos repetidos.

Uma contagem elevada de linhas melhora a cobertura de cenários de software, mas **não** autoriza tratá-las como 270.000 alunos independentes. A separação e o cálculo da incerteza devem respeitar a hierarquia dos dados.

## 4. Seeds e determinismo
**Seed** é uma semente numérica que inicializa decisões pseudoaleatórias. O relatório fixa a seed de seleção 20261029 e três seeds de divisão: 20261029, 20261030, 20261031. Cada seed de divisão produz um holdout distinto. Isso permite comparar sensibilidade à partição, mas os holdouts continuam compartilhando a mesma população sintética.

## 5. Riscos metodológicos
**Viés de simulação:** diferenças entre regras geradas e comportamento real. **Circularidade do alvo:** risco de os critérios do gerador, usados para produzir aprovação/reprovação, serem semelhantes às regras que o estimador aprende. **Mudança de domínio:** alterações nas distribuições de notas, frequência e gestão escolar, não observadas neste benchmark.

Para demonstrar generalização fora da população atual seria necessário treinar com uma população GENESIS e avaliar em outra, ou, preferencialmente, validar com dados reais autorizados. Essa etapa permanece fora do escopo congelado.

## 6. Reprodutibilidade prática
Um relatório reproduzível deve fixar código/commit, versões de dependências, identificador do manifesto, regras de seleção de alunos, seeds, recursos computacionais e esquema JSON. O benchmark local forneceu duração externa de **445,2471287 segundos**, mas não registrou pico de memória RSS.

## 7. Termos para glossário
**Parquet:** formato colunar usado em datasets analíticos. **Manifesto:** registro de conteúdo e parâmetros que descrevem os artefatos. **SHA-256:** resumo criptográfico de 256 bits usado para identificar bytes. **Proveniência:** histórico da origem e das transformações de dados. **População sintética:** conjunto gerado por regras computacionais, não coleta escolar observacional.'''),
'03':('MAPA temporal e prevenção de vazamento','Demonstrar por que N1, N2 e N3 só podem utilizar informações disponíveis no momento da predição.', '''## 1. Predição point-in-time
Um teste antecipado só é honesto quando a representação do estudante é construída **como seria no instante da decisão**. O MAPA exporta snapshots para N1, N2 e N3. Em N1 não se pode usar notas de N2, N3 ou N4; em N2 não se pode usar N3/N4; e em N3 o último período continua futuro.

![linha_tempo.png|Figura 1. Sequência conceitual de disponibilidade temporal; as setas não representam a inclusão de dados futuros.]

## 2. As onze features observadas
As entradas são `current_mean_grade`, `current_attendance_rate`, `current_absences`, `current_unexcused_absences`, `current_sessions`, `prior_mean_grade`, `prior_attendance_rate`, `prior_absences`, `prior_unexcused_absences`, `prior_term_count` e `prior_years_observed`. Em português: média atual, taxa de frequência atual, faltas atuais, faltas não justificadas atuais, sessões atuais e seis indicadores de histórico anterior.

O rótulo `target_final_subject_outcome` aparece no dataset de treinamento para supervisão, mas **não** deve ser fornecido como entrada. Atributos históricos devem referir-se a períodos anteriores, não a informações coletadas depois do corte.

## 3. Data leakage: quatro caminhos de erro
**Vazamento temporal:** calcular médias com avaliações posteriores. **Vazamento de alvo:** usar campo que determina diretamente o resultado final. **Vazamento entre alunos:** deixar linhas do mesmo aluno em treino e teste. **Vazamento de pré-processamento:** calcular normalização ou imputação com todos os dados, inclusive o teste.

O protocolo usa agrupamento por estudante e pipelines de pré-processamento ajustados somente em treino. Essas salvaguardas mitigam riscos específicos; não provam ausência absoluta de leakage em todas as transformações upstream.

## 4. Auditabilidade
Para cada corte deve ser possível indicar quais colunas foram lidas, qual manifesto autorizou seu uso e quantas observações entraram em treino/teste. A mesma lógica deve ser aplicada a validações futuras de múltiplas populações.

## 5. Evidência temporal no benchmark
O aumento do macro-F1 de N1 para N3 é compatível com a hipótese de que observações acadêmicas adicionais tornam o desfecho mais previsível dentro do gerador. Porém, como os alvos são produzidos sinteticamente, não se pode descartar que o padrão reflita principalmente as regras do simulador.

![macro_f1.png|Figura 2. Evolução da métrica de classificação nos cortes avaliados.]

## 6. Exemplo didático
Considere uma disciplina com N1 = 5,0 e N2 = 7,0. Para uma predição feita em N1, a média 6,0 seria informação proibida: N2 ainda não ocorreu. Mesmo que o modelo pareça melhorar com essa variável, o experimento teria invalidado o caráter antecipatório.

## 7. Termos para glossário
**Snapshot:** registro dos atributos disponíveis num instante. **Point-in-time:** regra que impede usar informação posterior à predição. **Data leakage:** vazamento de informação indevida para treinamento ou teste. **Imputação:** preenchimento controlado de valores ausentes. **Pipeline:** cadeia de transformações reproduzível.'''),
'04':('Particionamento, baselines e métricas','Formalizar como a avaliação é feita e como interpretar métricas de três classes sem depender apenas da acurácia.', '''## 1. Unidade independente e split
O experimento 5K dividiu 5.000 estudantes em grupos com 75% para treino e 25% para teste. **Todas as linhas de um mesmo estudante permanecem no mesmo lado**. Em uma divisão resultam 3.750 estudantes em treino e 1.250 em teste, com diversas observações disciplinares para cada aluno.

![split.png|Figura 1. Separação agrupada por estudante: disciplinas do mesmo aluno não atravessam o split.]

## 2. A matriz de confusão
Para cada uma das três classes, a matriz relaciona resultado observado (linha) e predito (coluna). A diagonal contabiliza acertos; os demais elementos identificam confusões. Por exemplo, classificar reprovado como recuperação é um erro que pode ser pedagogicamente relevante mesmo quando o número total de acertos permanece alto.

## 3. Precisão, recall e F1
Para a classe c, define-se TP como verdadeiro positivo, FP como falso positivo e FN como falso negativo. **Precisão = TP/(TP+FP)**. **Recall = TP/(TP+FN)**. **F1 = 2 × precisão × recall/(precisão+recall)**. O **macro-F1** é a média aritmética dos F1 das três classes; a **balanced accuracy** é a média dos recalls das classes. Denominadores nulos precisam ter regra explícita de tratamento.

**Acurácia** é o total de previsões corretas dividido pelo total de previsões. Uma estratégia que prevê sempre a classe predominante pode ter acurácia aparentemente aceitável enquanto falha em detectar reprovação. Por isso são indispensáveis macro-F1, recall por classe e baseline de maioria.

## 4. Métricas probabilísticas
O **log loss** penaliza probabilidades incorretas com grande confiança. O **Brier multiclasse** soma os quadrados das diferenças entre probabilidade prevista e indicador da classe verdadeira. Ambas são medidas probabilísticas cujo menor valor representa melhor pontuação, mas não demonstram isoladamente calibração perfeita.

## 5. Protocolos comparáveis
Comparações entre estimadores devem usar as mesmas divisões, cutoffs, classes e regras de preprocessamento. As três seeds geram três holdouts na mesma população; médias entre elas são descritivas, não nove ensaios independentes.

## 6. Resultado empírico sintético do 5K
O macro-F1 médio passou de aproximadamente 0,75 no N1 para 0,89 no N3 em ambos os modelos. O recall de reprovação no N1 ficou próximo de 50%, evidenciando que desempenho agregado não equivale a cobertura satisfatória da classe crítica.

![recall_reprovacao.png|Figura 2. Recall médio da classe reprovado nos três cortes.]

## 7. Termos para glossário
**TP/FP/FN:** contagens de acertos positivos, alarmes indevidos e casos perdidos. **Precisão:** fração de predições positivas corretas. **Recall/sensibilidade:** fração dos casos reais de uma classe recuperada pelo classificador. **Balanced accuracy:** recall médio entre classes. **Baseline:** referência simples a superar.'''),
'05':('Classificadores, arquitetura e treinamento','Descrever Logistic Regression, Random Forest e MLP, incluindo o escopo efetivamente treinado no avaliador 5K.', '''## 1. Família de modelos
O pipeline nativo suporta baseline por maioria, Regressão Logística, Random Forest e MLP. No **avaliador estatístico final 5K**, somente **Regressão Logística e MLP** foram selecionados; as demais famílias pertencem ao benchmark exploratório anterior e não devem ser inseridas em tabelas estatísticas 5K como se tivessem sido retreinadas.

## 2. Regressão Logística multiclasse
Apesar do nome, é um classificador probabilístico. Com um vetor de atributos x, estima escores lineares `z_c = w_c · x + b_c` e os converte em probabilidades por função softmax. Os parâmetros são ajustados para reduzir perda de classificação probabilística. A linearidade facilita reprodutibilidade e economia computacional, mas não garante interpretação causal dos coeficientes.

## 3. Perceptron multicamadas (MLP)
A arquitetura documentada para esta execução possui **11 entradas, duas camadas ocultas de 32 e 16 unidades e três saídas**. Cada neurônio calcula combinação ponderada seguida de transformação não linear. A previsão final é uma distribuição de probabilidades sobre as três classes. O gráfico apresenta a **topologia configurada**, não valores dos pesos nem ativação monitorada durante as épocas.

![mlp.png|Figura 1. Diagrama representativo da arquitetura 11–32–16–3 do MLP. Conexões resumidas para legibilidade.]

## 4. Random Forest como referência arquitetural
A Random Forest combina diversas árvores de decisão, cada uma com divisões sucessivas de atributos e limiares. A agregação das árvores busca reduzir variabilidade em relação a uma única árvore. O desenho é **didático**, não a estrutura aprendida por um estimador 5K.

![floresta.png|Figura 2. Ilustração esquemática de uma floresta de árvores, sem nós ou thresholds reais.]

## 5. Comparação numérica 5K
A Regressão Logística apresentou macro-F1 médio de 0,7540/0,8294/0,8934 (N1/N2/N3); o MLP apresentou 0,7578/0,8268/0,8933. A vantagem alterna entre cortes e os intervalos pareados não definem um vencedor geral. Dado o ganho modesto do MLP, o custo de ajuste precisa compor o critério de seleção.

## 6. Controle de treinamento
As seeds, limites amostrais, ordem das classes e versões das bibliotecas devem ser registradas. A escolha de hiperparâmetros não deve usar repetidamente o teste final. Para futuros ajustes de arquitetura ou limiar, é necessário separar validação independente agrupada por estudante.

## 7. Termos para glossário
**MLP:** rede neural feedforward de várias camadas. **Neurônio artificial:** operação de soma ponderada seguida de ativação. **Peso:** coeficiente aprendido. **Softmax:** função de normalização de escores em probabilidades. **Random Forest:** conjunto de árvores. **Hiperparâmetro:** configuração escolhida antes do ajuste.'''),
'06':('Bootstrap agrupado e incerteza estatística','Explicar intervalos bootstrap por estudante, pareamento e limites das inferências obtidas.', '''## 1. Por que a unidade de reamostragem importa
Registros de disciplinas de um mesmo estudante compartilham fatores não observados e trajetórias. Aplicar bootstrap sobre linhas como se fossem independentes pode produzir estimativas de incerteza artificialmente estreitas. O protocolo usa **bootstrap por cluster de estudante**: sorteia IDs de alunos do conjunto de teste com reposição e incorpora todas as respectivas observações.

## 2. Procedimento
Para cada cutoff/seed: (1) ajustam-se ambos os modelos no mesmo treino; (2) obtêm-se as previsões nos mesmos alunos de teste; (3) sorteiam-se 1.250 IDs com reposição, repetindo o processo 200 vezes; (4) soma-se, para cada reamostragem, a matriz de confusão acumulada dos alunos sorteados; (5) calcula-se novo macro-F1; (6) usam-se os quantis 2,5% e 97,5% para formar o intervalo percentílico de 95%.

## 3. Diferença pareada
A comparação usa **o mesmo sorteio de estudantes** para Regressão Logística e MLP, calculando `Δ = F1_macro(Logística) − F1_macro(MLP)`. Se Δ é positivo, a Logística tem F1 maior naquela reamostragem; se negativo, o MLP. O método pareado isola parte da variação causada pela composição do teste.

![pareados.png|Figura 1. Estimativas e intervalos percentílicos pareados (95%) no experimento sintético 5K.]

## 4. Interpretação dos nove intervalos
No 5K, seis dos nove intervalos cruzam zero. Um intervalo no N1 (seed 20261031) favorece a MLP; dois no N2 (seeds 20261029 e 20261030) favorecem a Regressão Logística. Todos os intervalos no N3 incluem zero. Não há vantagem estável de um modelo para os três cortes.

A frequência de deltas positivos no bootstrap é um **indicador descritivo**, não um p-valor. Nove comparações exploratórias também exigiriam tratamento de multiplicidade para inferência confirmatória.

## 5. O que o intervalo NÃO mede
Os intervalos são condicionais ao ajuste do modelo e à amostra sintética de estudantes usada para teste. Não incorporam reamostragem do treinamento, variação de escolas ou migração para novas populações. Três seeds de holdout na mesma população não equivalem a três amostras externas independentes.

## 6. Exemplo intuitivo
Se um estudante produz vinte registros de disciplinas e anos, o sorteio dele deve trazer todo esse conjunto, preservando a correlação. Selecionar aleatoriamente dez desses registros produziria um mundo artificial em que a dependência intraestudante desaparece.

## 7. Termos para glossário
**Bootstrap:** reamostragem computacional com reposição. **Cluster:** grupo de observações correlacionadas, aqui o estudante. **IC 95%:** intervalo estimado por procedimento estatístico sob determinadas suposições, não garantia de 95% de probabilidade para o parâmetro fixo. **Quantil:** ponto de uma distribuição ordenada. **Pareamento:** comparação sob as mesmas unidades de teste.'''),
'07':('Calibração, log loss e pontuações probabilísticas','Contextualizar a confiabilidade das probabilidades, diferenciando medidas de pontuação de calibração demonstrada.', '''## 1. Probabilidade como saída de decisão
Um classificador pode acertar a classe mais provável e ainda informar probabilidades exageradas ou conservadoras. Para aplicações educacionais, uma previsão de 0,85 para reprovação precisa ser interpretada com cuidado: se os eventos previstos com esse grau de confiança ocorrerem apenas 0,50 das vezes, a probabilidade está mal calibrada.

## 2. Log loss e Brier
O **log loss** cresce muito quando um modelo atribui probabilidade pequena ao resultado que efetivamente ocorreu. O **Brier multiclasse** é uma pontuação quadrática entre probabilidades e vetores indicadores das classes. Ambas são *proper scoring rules*, úteis para avaliar qualidade global das probabilidades.

No benchmark 5K, log loss médio N1→N3: Regressão Logística 0,3912→0,1759; MLP 0,3827→0,1769. A diminuição é consistente com previsões probabilísticas melhores em cortes tardios, mas não prova calibração por subgrupos ou aplicação real.

![log_loss.png|Figura 1. Log loss médio das três divisões do experimento 5K.]

## 3. Confiabilidade descritiva
A análise produz **reliability bins**: agrupa probabilidades previstas em dez faixas e compara probabilidade média com frequência observada. O procedimento é calculado para a classe mais provável (top-label) e em abordagem um-contra-o-resto para cada classe. **ECE**, erro esperado de calibração, resume diferenças absolutas ponderadas pelos tamanhos das faixas.

A ECE depende do número e da ocupação dos bins; valores baixos podem ocultar divergências em faixas raras ou grupos minoritários. Ela não equivale a calibrar o classificador. **Nenhum recalibrador foi ajustado** neste ensaio, e fazê-lo sobre o conjunto final de teste criaria leakage.

## 4. Classe minoritária
Reprovação representa cerca de 5%–6% das observações nos holdouts 5K. Uma ECE baixa pode ser dominada pelas numerosas previsões de probabilidade próxima a zero; examinar faixas com suporte pequeno e erros falsos-negativos ainda é obrigatório.

## 5. Protocolo de calibração futura
Uma evolução adequada deve separar treino, validação agrupada para calibrador/limiares e teste final intocado. Métodos como sigmoid/Platt ou isotonic podem ser comparados sob essa separação, mas não estão presentes no conjunto congelado.

## 6. Termos para glossário
**Calibração:** correspondência entre confiança prevista e frequência observada. **Reliability diagram:** gráfico de confiança versus frequência. **ECE:** resumo dependente de faixas do erro de calibração. **Log loss:** penalidade logarítmica probabilística. **Brier score:** perda quadrática probabilística. **One-vs-rest:** análise de uma classe contra todas as demais.'''),
'08':('Resultados comparativos e análise de erros','Consolidar os resultados sintéticos 5K, sua evolução temporal e o problema dos falsos negativos de reprovação.', '''## 1. Matriz de resultados do experimento final
O ensaio 5K utilizou 5.000 estudantes sintéticos, três seeds de split e cortes N1/N2/N3. As médias aritméticas de métricas são descritivas e não são intervalos de confiança entre três populações.

| Corte | Modelo | Acurácia | Macro-F1 | Recall reprovação | Log loss |
| --- | --- | --- | --- | --- | --- |
| N1 | Logística | 0,8259 | 0,7540 | 0,5025 | 0,3912 |
| N1 | MLP | 0,8291 | 0,7578 | 0,5099 | 0,3827 |
| N2 | Logística | 0,8772 | 0,8294 | 0,6671 | 0,2794 |
| N2 | MLP | 0,8767 | 0,8268 | 0,6518 | 0,2774 |
| N3 | Logística | 0,9224 | 0,8934 | 0,8033 | 0,1759 |
| N3 | MLP | 0,9217 | 0,8933 | 0,8266 | 0,1769 |

![macro_f1.png|Figura 1. Comparação do macro-F1 médio por corte.]

## 2. A dificuldade da predição antecipada
O maior erro qualitativo é a identificação insuficiente de reprovação no primeiro corte. O recall de reprovado gira em torno de 50% em N1, melhora para 65%–67% em N2 e atinge cerca de 80%–83% em N3. O modelo precisa equilibrar antecedência e informação disponível: prever cedo é mais útil para intervir, mas é estatisticamente mais incerto.

![recall_reprovacao.png|Figura 2. Evolução do recall de reprovação nos cortes.]

## 3. Por que não basta a acurácia
Aprovação é frequente; um classificador pode acertar muitos aprovados e ainda negligenciar reprovados. Macro-F1 fornece peso igual às três classes. Recall de reprovação esclarece a fração dos casos críticos identificados; isoladamente, porém, não informa quantos alertas falsos foram criados. A inspeção conjunta de precisão, recall e matriz de confusão é essencial.

## 4. Alternância entre modelos
A MLP apresenta macro-F1 ligeiramente maior em N1; a Logística tem pequena vantagem em N2 e praticamente empata no N3. A análise de intervalos pareados não sustenta declarar um vencedor universal. Recomenda-se manter a Logística como referência de baixo custo e a MLP como comparador de capacidade não linear.

## 5. Resultados não demonstrados
O experimento não mediu efetividade de intervenções, evasão real, impacto em professores, generalização entre escolas ou desempenho em grupos demográficos. Não atribuir esses efeitos aos resultados apresentados.

## 6. Termos para glossário
**Falso negativo:** caso real de reprovação não identificado. **Falso positivo:** aviso de reprovação quando o desfecho é outro. **Trade-off:** compromisso entre objetivos em tensão, como antecedência e sensibilidade. **Support:** número de observações reais de cada classe.'''),
'09':('Escalabilidade, custo e reprodutibilidade','Apresentar custo do benchmark 5K e diferenciar duração total de tempo de ajuste dos modelos.', '''## 1. Estrutura computacional do benchmark
O teste 5K utiliza 18 ajustes: 3 cutoffs × 3 seeds × 2 algoritmos. A cada combinação há seleção de grupos, leitura dos atributos, ajuste, previsão, cálculo de métricas e bootstrap com 200 reamostragens por grupo de estudantes.

## 2. Tempo observado
O comando externo PowerShell `Measure-Command` registrou **445,2471287 segundos** (cerca de 7 min e 25 s) para todo o processo. Essa medida envolve inicialização do Python, carga de dados, transformação, ajuste, predição, intervalos e gravação do JSON. Não constitui média de múltiplas execuções com controle de ambiente.

Os ajustes individuais apresentaram médias em segundos: Logística N1=2,44, N2=1,65, N3=1,89; MLP N1=32,10, N2=30,18, N3=31,14. O custo do MLP foi substancialmente maior que o linear.

![tempos_fit.png|Figura 1. Tempo de ajuste por modelo e corte (média de três seeds, 5K).]

## 3. Escala ≠ generalização
Confrontos preliminares com 500 e 2.000 estudantes apontaram estabilidade do macro-F1, mas, para um quadro comparativo definitivo, os JSONs dessas execuções devem integrar o conjunto versionado de evidências e ser associados aos respectivos hashes. O congelamento deste volume privilegia o relatório 5K, disponibilizado e verificado.

## 4. Perfil de memória e processamento
O avaliador usa etapas em memória e leitura analítica do Parquet. **Não existe medição de pico RSS no relatório 5K.** Portanto, é inadequado afirmar consumo máximo de RAM ou eficiência out-of-core. Fit time não inclui bootstrap nem E/S, e o total de execução não equivale exclusivamente ao tempo de treinamento.

## 5. Manifestos e rastreabilidade
O hash do manifesto de entrada é `ec863d9f267564e27adf1a701f88951cf064af744eb2452708f120c22d947f23`. O registro documental aponta SHA-256 do JSON final `903298722b6b44cd9f955ee4ece73419781c3933deea27f1393ad84846f37836`. Um hash só é útil se for verificado contra os mesmos bytes e acompanhado de identificação do código e das dependências.

## 6. Critério de congelamento
Os dados e resultados podem ser congelados para escrita como **ensaio sintético controlado**. Novas versões devem criar novos identificadores, jamais sobrescrever artefatos e conclusões anteriores. A reprodução completa em outra máquina depende da publicação de dependências e geradores compatíveis.

## 7. Termos para glossário
**RSS:** memória física residente em um processo. **Fit time:** tempo estrito de ajuste do estimador. **Wall time:** tempo transcorrido de ponta a ponta. **Out-of-core:** processamento sem manter todo o conjunto em RAM. **Escalabilidade:** evolução do custo computacional com tamanho do problema.'''),
'10':('Síntese científica, limites e protocolo de escrita','Definir quais afirmações podem entrar no artigo v0.3, como referenciar evidências e que perguntas ficam para trabalhos posteriores.', '''## 1. O que os experimentos permitem afirmar
O MAPA implementa um protocolo de classificação de desfecho por disciplina em três cortes temporais sintéticos. O relatório 5K reúne três holdouts agrupados por estudante, duas famílias de modelos e bootstrap agrupado. O macro-F1 cresce com a aproximação do fim do ano; a MLP não estabelece vantagem estável sobre a Regressão Logística.

## 2. O que permanece indeterminado
Não foi provada generalização entre escolas, alunos reais ou populações sintéticas independentes. A identificação precoce de reprovação em N1 ainda apresenta recall próximo de 50%. A análise probabilística contém log loss, Brier e ECE descritiva, **não** recalibração validada. O sistema não foi avaliado quanto a efeitos causais de intervenção, justiça distributiva ou previsões de evasão.

## 3. Como escrever o artigo
Cada resultado quantitativo deve ser acompanhado de **unidade de análise**, definição de classes, corte, modelos, protocolo de split, número de estudantes, intervalo e origem do artefato. Diferenciar «resultado observado», «interpretação compatível» e «hipótese ainda não testada». Evitar frases como «94% de acerto comprova impacto pedagógico» quando a medida foi sintética ou veio de uma versão anterior do sistema.

## 4. Estrutura sugerida para o Full Paper
(1) Introdução e problema; (2) Trabalhos relacionados e escolhas algorítmicas; (3) Materiais e métodos, GENESIS e point-in-time MAPA; (4) Protocolo experimental e métricas; (5) Resultados sintéticos e intervalos pareados; (6) Limitações e ameaças à validade; (7) Conclusão. Conservar a exigência de encerramento com seção intitulada **Conclusão**.

## 5. Plano de evidências
O corpo do artigo deve referenciar o manifesto de features, os comandos, as seeds, o arquivo JSON do benchmark, os gráficos derivados dele e os testes automatizados. O apêndice ou cadernos científicos fornece as explicações matemáticas sem tornar o artigo excessivamente longo.

![pareados.png|Figura 1. Comparação pareada para fundamentar a ausência de vencedor universal.]

## 6. Conclusão para o recorte sintético
Os resultados demonstram que a infraestrutura consegue executar uma avaliação sintética reprodutível de classificação acadêmica temporal e identificar diferenças de comportamento entre cortes. Não demonstram, por si, validade externa, segurança de implantação escolar ou benefício pedagógico. Essa separação é fundamental para uma comunicação científica responsável.

## 7. Glossário e leitura orientada
Os termos técnicos usados ao longo dos dez cadernos são consolidados no arquivo `GLOSSARIO.md`, com definições curtas, analogias e cuidados de interpretação. Um leitor sem formação em ML deve conseguir associar cada gráfico a uma pergunta simples: o que foi previsto, com que informação, para quem e com qual incerteza.''')
}

REFERENCE='''## Referências e rastreabilidade
[1] Gneiting, T.; Raftery, A. E. (2007). Strictly Proper Scoring Rules, Prediction, and Estimation. *Journal of the American Statistical Association*, 102(477), 359–378. DOI: 10.1198/016214506000001437.
[2] Efron, B.; Tibshirani, R. (1993). *An Introduction to the Bootstrap*. Chapman & Hall.
[3] scikit-learn developers. User Guide: Model evaluation, Probability calibration, GroupShuffleSplit, MLPClassifier. https://scikit-learn.org/stable/user_guide.html (consulta metodológica; versão efetiva do ambiente deve ser registrada).
[4] EduPredict Analytics. Relatório técnico interno MAPA 5K, schema `epa.mapa.statistical_evaluation.v1`; manifesto `ec863d9f267564e27adf1a701f88951cf064af744eb2452708f120c22d947f23`; população sintética e três seeds, novembro de 2026.
'''
GLOSSARY='''# Glossário técnico cumulativo — EduPredict Analytics

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
'''

for code,(title,objective,body) in CHAPTERS.items():
 doc=f'''# C{code} — {title}\n\n**EduPredict Analytics (EPA) · Cadernos de Pesquisa · TGI II**  \n**Carlos Eduardo Franco Gabriel · Miguel Ferreira Palmieri Souza Rocha**  \n**Universidade Cruzeiro do Sul — Ciência da Computação — São Paulo, Brasil**  \n**Orientador: Prof. Me. João Roberto Ursino da Cruz**  \n**Versão:** 0.3 (congelamento sintético de 12 nov. 2026)  \n**Status:** SYNTHETIC_NOT_EMPIRICALLY_VALIDATED\n\n**Resumo.** {objective} O documento distingue resultados medidos, explicação técnica e inferências limitadas à população sintética GENESIS.\n\n**Palavras-chave.** EduPredict Analytics; avaliação temporal; dados sintéticos; rastreabilidade; aprendizado de máquina.\n\n{body}\n\n{REFERENCE}'''
 (SOURCE/f'C{code}.md').write_text(doc,encoding='utf-8')
(SOURCE/'GLOSSARIO.md').write_text(GLOSSARY,encoding='utf-8')

# A4 SBC-inspired academic layout based on project article v0.2; not official SBC class.
FONT='/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf'; BOLD='/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf';ITALIC='/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf'
pdfmetrics.registerFont(TTFont('LibSerif',FONT));pdfmetrics.registerFont(TTFont('LibSerif-Bold',BOLD));pdfmetrics.registerFont(TTFont('LibSerif-Italic',ITALIC));pdfmetrics.registerFontFamily('LibSerif',normal='LibSerif',bold='LibSerif-Bold',italic='LibSerif-Italic',boldItalic='LibSerif-Bold')
styles={
 'title':ParagraphStyle('title',fontName='LibSerif-Bold',fontSize=15,leading=18,alignment=TA_CENTER,spaceAfter=12),
 'meta':ParagraphStyle('meta',fontName='LibSerif',fontSize=9,leading=12,alignment=TA_CENTER,spaceAfter=3),
 'body':ParagraphStyle('body',fontName='LibSerif',fontSize=10.5,leading=14,alignment=TA_JUSTIFY,spaceAfter=7),
 'h':ParagraphStyle('h',fontName='LibSerif-Bold',fontSize=12,leading=15,spaceBefore=13,spaceAfter=6,keepWithNext=True),
 'caption':ParagraphStyle('caption',fontName='LibSerif',fontSize=9,leading=11,alignment=TA_CENTER,spaceAfter=10),
 'small':ParagraphStyle('small',fontName='LibSerif',fontSize=8.8,leading=11.3,alignment=TA_LEFT,spaceAfter=6),
 'table':ParagraphStyle('table',fontName='LibSerif',fontSize=9,leading=11),
}

def inline(s):
 s=escape(s)
 s=re.sub(r'\*\*(.+?)\*\*',r'<b>\1</b>',s)
 s=re.sub(r'`([^`]+)`',r'<font color="#1e605a">\1</font>',s)
 s=re.sub(r'\*(.+?)\*',r'<i>\1</i>',s)
 return s

def add_page(c,doc):
 w,h=A4;c.setFillColor(colors.HexColor('#56706d'));c.setFont('LibSerif',8.5)
 c.drawString(54,h-36,'EDUPREDICT ANALYTICS · CADERNOS CIENTÍFICOS · TGI II')
 c.setStrokeColor(colors.HexColor('#b7cec9'));c.line(54,h-43,w-54,h-43)
 c.setStrokeColor(colors.HexColor('#b7cec9'));c.line(54,45,w-54,45)
 c.drawString(54,32,'EPA · Resultados sintéticos · Versão técnica 0.3');c.drawRightString(w-54,32,str(doc.page))

def make_pdf(code,path):
 raw=path.read_text(encoding='utf-8');lines=raw.splitlines(); story=[];i=0
 while i<len(lines):
  line=lines[i].strip(); i+=1
  if not line:continue
  if line.startswith('# '):story.append(Paragraph(inline(line[2:]),styles['title']));continue
  if line.startswith('## '):story.append(Paragraph(inline(line[3:]),styles['h']));continue
  if line.startswith('!['):
   m=re.match(r'!\[([^|\]]+)\|([^\]]+)\]',line)
   if m and (FIG/m.group(1)).exists():
    from PIL import Image as PILImage
    wi,he=PILImage.open(FIG/m.group(1)).size; dispw=487;disph=dispw*he/wi
    if disph>245:disph=245;dispw=disph*wi/he
    story.append(Image(str(FIG/m.group(1)),width=dispw,height=disph,hAlign='CENTER'))
    story.append(Paragraph(inline(m.group(2))+'<br/><i>'+inline(FONTE)+'</i>',styles['caption']))
   continue
  if line.startswith('|'):
   rows=[line]
   while i<len(lines) and lines[i].lstrip().startswith('|'):rows.append(lines[i].strip());i+=1
   filtered=[r for r in rows if not re.match(r'^\|[\s:|\-]+\|$',r)]
   cells=[[Paragraph(inline(c.strip()),styles['table']) for c in r.strip('|').split('|')] for r in filtered]
   t=Table(cells,colWidths=[(A4[0]-108)/len(cells[0])]*len(cells[0]),repeatRows=1,hAlign='CENTER')
   t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e9f1ed')),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('BOTTOMPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),6),('LINEBELOW',(0,0),(-1,0),.6,colors.HexColor('#6f9791')),('LINEBELOW',(0,1),(-1,-1),.25,colors.HexColor('#d0d7d6'))]))
   story.append(t);story.append(Spacer(1,8));continue
  if line.startswith('**EduPredict') or line.startswith('**Carlos') or line.startswith('**Universidade') or line.startswith('**Orientador') or line.startswith('**Versão') or line.startswith('**Status'):
   story.append(Paragraph(inline(line.rstrip('  ')),styles['meta']));continue
  para=[line]
  while i<len(lines) and lines[i].strip() and not lines[i].startswith(('#','![','|')):
   para.append(lines[i].strip());i+=1
  story.append(Paragraph(inline(' '.join(para)), styles['body']))
 doc=SimpleDocTemplate(str(PDF/f'C{code}_EPA_SBC.pdf'),pagesize=A4,leftMargin=54,rightMargin=54,topMargin=59,bottomMargin=57,title=f'EPA Caderno C{code}',author='Carlos Eduardo Franco Gabriel; Miguel Ferreira Palmieri Souza Rocha')
 doc.build(story,onFirstPage=add_page,onLaterPages=add_page)

for code in CHAPTERS:make_pdf(code,SOURCE/f'C{code}.md')
# glossary also rendered as an appendix PDF
glossary_lines=GLOSSARY.splitlines();story=[Paragraph('Glossário técnico — EduPredict Analytics',styles['title'])]
for line in glossary_lines[1:]:
 if not line.strip():continue
 story.append(Paragraph(inline(line),styles['body']))
SimpleDocTemplate(str(PDF/'GLOSSARIO_EPA_SBC.pdf'),pagesize=A4,leftMargin=54,rightMargin=54,topMargin=59,bottomMargin=57,title='Glossário EPA',author='EduPredict Analytics').build(story,onFirstPage=add_page,onLaterPages=add_page)
print(json.dumps({'pdfs':[x.name for x in sorted(PDF.glob('*.pdf'))],'pages':__import__('pypdf').PdfReader(str(PDF/'C08_EPA_SBC.pdf')).get_num_pages()}))