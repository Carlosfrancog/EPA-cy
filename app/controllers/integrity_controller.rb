class IntegrityController < ApplicationController
  def index
    @audits = MapaRun.where(status: "completed").order(id: :desc).limit(20).map { |run| MapaIntegrityAudit.inspect_run(run) }
    @checks = [
      ["SHA-256", "Verificação local de digest de artefato MAPA", "Operacional"],
      ["Temporalidade", "Checagem de dependências declaradas", "Protótipo"],
      ["Proveniência", "Comparação de hash, schema e seed entre artefatos", "Operacional"],
      ["Assinaturas", "Atestação verificável e âncora externa", "Planejado"],
      ["Workers", "Execução em containers com permissões mínimas", "Planejado"]
    ]
  end
end
