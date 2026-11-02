class IntegrityController < ApplicationController
  def index
    @audits = MapaRun.where(status: "completed").order(id: :desc).limit(20).map { |run| MapaIntegrityAudit.inspect_run(run) }
    @scientific_audits = MapaRun.where(status: "completed").order(id: :desc).limit(20).map do |run|
      { run_id: run.id, reports: SentinelResearchAudit.inspect_run(run) }
    end
    @checks = [
      ["SHA-256", "Verificação local de digest de artefato MAPA", "Operacional"],
      ["Temporalidade", "Auditoria estrutural de GroupKFold e estado temporal declarado", "Operacional (declarativo)"],
      ["Proveniência", "Comparação de hash, schema e seed entre artefatos", "Operacional"],
      ["Assinaturas", "Atestação verificável e âncora externa", "Planejado"],
      ["Workers", "Execução em containers com permissões mínimas", "Planejado"]
    ]
  end
end
