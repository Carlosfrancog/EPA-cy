class IntegrityController < ApplicationController
  def index
    @checks = [
      ["SHA-256", "Verificação de digest de artefato", "Protótipo"],
      ["Temporalidade", "Checagem de dependências declaradas", "Protótipo"],
      ["Proveniência", "Cadeia local de hashes do EPA Ledger", "Protótipo"],
      ["Assinaturas", "Atestação verificável e âncora externa", "Planejado"],
      ["Workers", "Execução em containers com permissões mínimas", "Planejado"]
    ]
  end
end
