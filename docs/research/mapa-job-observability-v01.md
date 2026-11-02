# Observabilidade MAPA v0.1

O painel de histórico mostra estados, duração média e execuções em andamento há mais de quinze minutos nas últimas trinta execuções. Calcula dados exclusivamente a partir de timestamps persistidos. Ausência de horário gera duração indisponível. Alerta não comprova travamento, não reinicia e não cancela jobs.

O worker emite eventos estruturados com run_id, job_id e código de falha, sem dados individuais dos alunos ou conteúdo dos relatórios. Sem migração e sem alteração do contrato científico/MLflow.
