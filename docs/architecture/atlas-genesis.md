# Atlas + Genesis v0

## Atlas
Fonte oficial de contexto: https://basenacionalcomum.mec.gov.br/ e https://downloadbncc.mec.gov.br/

O arquivo demonstrativo é **sintético** e não reproduz habilidades oficiais nem representa grade curricular adotada por uma escola real. Os níveis 6–9 representam Ensino Fundamental e 10–12 representam 1º–3º do Ensino Médio na convenção interna do gerador.

## Genesis
```bash
python -m pip install -e ".[research,dev]"
python -m epa.genesis.generate --output data/demo --students 100 --seed 20261029
pytest -q
```

Em `data/demo`, são produzidos `academic_history.parquet` e `manifest.json`. A versão v0 é **in-memory** e limitada a 50 mil estudantes: não é ainda a geração escalável por partitions/workers.

Atributos de cada linha: `student_id` sintético, ano, série, disciplina, área, nota final, frequência e classificação. As notas vêm de uma função estocástica artificial com traços persistentes e tendência por aluno. NÃO constituem dados educacionais reais nem comprovam perfis de alunos.

O manifesto usa SHA-256, mas **não há assinatura ou vínculo automático** ao Ledger/Sentinel. O avanço para dados oficiais requer revisão documental e importação rastreada.
