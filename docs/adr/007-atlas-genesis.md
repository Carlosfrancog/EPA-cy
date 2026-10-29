# ADR-007 — EPA Atlas e Genesis: dados sintéticos longitudinais

Status: aprovado como incremento experimental.

Atlas registra currículos explícitos, suas fontes, versões e configurações por série. A BNCC é referência normativa, não grade única de notas e disciplinas. **O arquivo examples/atlas.demo.json é uma matriz curricular fictícia**, destinada somente à demonstração e sem mapeamento oficial validado de habilidades.

Genesis gera estudantes sintéticos com traços de desempenho correlacionados ao longo dos anos, por área, disciplina e frequência; gera Parquet usando DuckDB e manifesto SHA-256. As regras escolhidas são artificiais, não foram calibradas nem validadas em dados escolares reais.

Regras: seeds e versões registradas, nunca sobrescrever output existente; nenhuma informação pessoal; não inferir deficiências reais nem perfis pedagógicos confirmados.

Evoluções: importação verificável de dados oficiais BNCC, versões curriculares por período, avaliações por bimestre, ausências por evento, independência entre geração e simulação de perfis, particionamento de bilhões de eventos, assinatura e vínculo ao Sentinel/Ledger.

Testes: geração determinística, mudança de seed, esquema curricular, exportação e digest de Parquet.
