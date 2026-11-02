# SENTINEL v0.1: structural checks against persisted research summaries.
# This audit cannot reconstruct student-ID disjointness from aggregated reports.
class SentinelResearchAudit
  SOURCES = {
    "MAPA CV" => [:research_report, "epa.mapa.research_protocol.v2"],
    "Modelos estendidos CV" => [:research_extended_report, "epa.mapa.research_extended.v1"]
  }.freeze
  EXPECTED_PROTOCOLS = %w[early trajectory consolidated].freeze

  def self.inspect_run(run)
    SOURCES.map do |name, (reader, schema)|
      report = run.public_send(reader)
      next { name: name, status: "absent", findings: ["Relatório não disponível."] } unless report
      source = report["source_manifest_sha256"]
      unless report["schema_version"] == schema &&
             report["dataset_classification"] == "SYNTHETIC" &&
             source.is_a?(String) && source == run.dataset_manifest_sha256 &&
             report["seed"] == run.seed
        next { name: name, status: "invalid", findings: ["Proveniência científica divergente."] }
      end
      protocols = report["protocols"]
      unless protocols.is_a?(Array) && protocols.map { |item| item.is_a?(Hash) ? item["protocol"] : nil } == EXPECTED_PROTOCOLS
        next { name: name, status: "invalid", findings: ["Protocolos N1/N2/N3 ausentes ou fora de ordem."] }
      end
      findings = []
      protocols.each do |block|
        tag = "N#{block["cutoff_term"]}"
        findings << "#{tag}: GroupKFold não declarado." unless block["fold_strategy"] == "GroupKFold_by_student"
        count = block["n_splits"]
        unless count.is_a?(Integer) && count.between?(2, 10)
          findings << "#{tag}: quantidade de folds inválida."
          next
        end
        folds = block["folds"]
        if !folds.is_a?(Array) || folds.empty?
          findings << "#{tag}: folds ausentes."
          next
        end
        folds.each do |fold|
          unless fold.is_a?(Hash) && fold["fold"].is_a?(Integer) && fold["fold"].between?(1, count)
            findings << "#{tag}: identificador de fold inválido."
            next
          end
          next if fold["status"] == "skipped"
          if !fold["train_students"].is_a?(Integer) || fold["train_students"] <= 0 ||
             !fold["test_students"].is_a?(Integer) || fold["test_students"] <= 0
            findings << "#{tag}: contagens de estudantes inválidas."
          end
          support = fold["class_support"]
          if !support.is_a?(Hash) || !%w[approved recovery failed].all? { |key| support[key].is_a?(Integer) && support[key] >= 0 }
            findings << "#{tag}: suporte de classes inválido."
          end
        end
        temporal = block["temporal_holdout"]
        if !temporal.is_a?(Hash) || !%w[evaluated not_identifiable].include?(temporal["status"])
          findings << "#{tag}: estado temporal desconhecido."
        elsif temporal["status"] == "not_identifiable"
          findings << "#{tag}: validação temporal não identificável (não é falha de integridade)."
        end
      end
      blocking = findings.reject { |msg| msg.include?("não identificável") }
      { name: name, status: blocking.empty? ? "checked" : "warning", findings: findings.uniq }
    end
  end
end
