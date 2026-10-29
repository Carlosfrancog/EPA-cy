class ArchitectureController < ApplicationController
  def index
    @components = [
      ["EPA ATLAS", "Registro e validação curricular", "atlas"],
      ["EPA GENESIS", "Geração longitudinal sintética", "genesis"],
      ["EPA CORE ENGINE", "Features e avaliação de modelos", "core"],
      ["EPA SENTINEL", "Políticas, integridade e admissibilidade", "sentinel"],
      ["EPA LEDGER", "Evidências e cadeia de auditoria", "ledger"]
    ]
  end
end
