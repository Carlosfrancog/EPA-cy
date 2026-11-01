# Transparent research-evidence gates, NOT a deployment or champion selector.
class MapaEvidenceGates
  PROTOCOLS = %w[early trajectory consolidated].freeze
  MODELS = %w[majority logistic_regression random_forest].freeze

  def self.assess(run, protocol:, model:)
    raise ArgumentError, "invalid protocol" unless PROTOCOLS.include?(protocol)
    raise ArgumentError, "invalid model" unless MODELS.include?(model)
    reasons = []
    evidence = run.research_report
    unless evidence.is_a?(Hash) && evidence["schema_version"] == "epa.mapa.research_protocol.v2" &&
           evidence["dataset_classification"] == "SYNTHETIC" &&
           evidence["source_manifest_sha256"] == run.dataset_manifest_sha256 &&
           evidence["seed"] == run.seed
      return { status: "insufficient_evidence", reasons: ["Protocolo científico ausente ou sem correspondência de proveniência."] }
    end
    block = evidence.fetch("protocols", []).find { |p| p.is_a?(Hash) && p["protocol"] == protocol }
    summary = block&.fetch("summaries", [])&.find { |s| s.is_a?(Hash) && s["model"] == model }
    distribution = summary&.dig("f1_macro_fold_distribution")
    unless distribution.is_a?(Hash) &&
           distribution["n_folds"].is_a?(Integer) && distribution["n_folds"] >= 3 &&
           %w[mean min max std].all? { |key| distribution[key].is_a?(Numeric) && distribution[key].finite? }
      reasons << "Validação cruzada insuficiente: mínimo de três folds válidos."
    end
    if summary && summary["missing_class_folds"].is_a?(Integer) && summary["missing_class_folds"] > 0
      reasons << "Há folds com classes ausentes no teste."
    elsif !summary || !summary["missing_class_folds"].is_a?(Integer)
      reasons << "Cobertura das classes não comprovada."
    end
    temporal = block&.dig("temporal_holdout")
    unless temporal.is_a?(Hash) && temporal["status"] == "evaluated" &&
           temporal["models"].is_a?(Array) && temporal["models"].any? { |m| m["model"] == model }
      reasons << "Validação temporal independente não disponível."
    end
    reasons << "Dados exclusivamente sintéticos; validação externa real pendente."
    { status: "research_only", reasons: reasons,
      cv_f1_mean: distribution.is_a?(Hash) ? distribution["mean"] : nil,
      temporal_status: temporal.is_a?(Hash) ? temporal["status"] : "unknown",
      deployable: false }
  end
end
