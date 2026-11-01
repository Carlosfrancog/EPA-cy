# Frozen per-report comparison: descriptive, not empirical champion promotion.
class MapaEvaluation
  PROTOCOLS = %w[early trajectory consolidated].freeze
  MODELS = %w[majority logistic_regression random_forest].freeze
  METRICS = %w[f1_macro balanced_accuracy accuracy].freeze

  def self.build(runs, protocol: "early", metric: "f1_macro", model: "all")
    raise ArgumentError, "invalid protocol" unless PROTOCOLS.include?(protocol)
    raise ArgumentError, "invalid metric" unless METRICS.include?(metric)
    raise ArgumentError, "invalid model" unless model == "all" || MODELS.include?(model)

    rows = []
    runs.each do |run|
      report = run.report
      next unless report.is_a?(Hash)
      next unless report["schema_version"] == "epa.mapa.benchmark.v1"
      next unless report["dataset_classification"] == "SYNTHETIC"
      block = report.fetch("baselines", []).find { |item| item["protocol"] == protocol }
      next unless block.is_a?(Hash)
      support = block["test_class_counts"]
      next unless support.is_a?(Hash) && %w[approved recovery failed].all? { |key| support[key].is_a?(Integer) && support[key] >= 0 }
      total = support.values_at("approved", "recovery", "failed").sum
      next unless total > 0
      block.fetch("results", []).each do |result|
        next unless result.is_a?(Hash) && MODELS.include?(result["model"])
        next if model != "all" && model != result["model"]
        next unless METRICS.all? { |name| result[name].is_a?(Numeric) && result[name].finite? && result[name].between?(0, 1) }
        recalls = result["recall_by_class"]
        next unless recalls.is_a?(Hash)
        next unless %w[approved recovery failed].all? { |key| recalls[key].is_a?(Numeric) && recalls[key].finite? && recalls[key].between?(0, 1) }
        rows << { run_id: run.id, seed: run.seed, protocol: protocol,
                  model: result["model"], score: result.fetch(metric),
                  accuracy: result["accuracy"], balanced_accuracy: result["balanced_accuracy"],
                  f1_macro: result["f1_macro"], recalls: recalls,
                  support: support, test_observations: total,
                  dataset_sha256: run.dataset_manifest_sha256 }
      end
    end
    rows.sort_by! { |r| [-r[:score], r[:model], r[:run_id]] }
    {
      rows: rows,
      best_per_model: MODELS.filter_map { |name| rows.find { |r| r[:model] == name } },
      evaluated_runs: rows.map { |r| r[:run_id] }.uniq.count,
      metric: metric, protocol: protocol, model: model,
      warnings: [
        "Ranking descritivo de holdouts sintéticos: não representa validação externa.",
        "Seeds e versões do dataset podem diferir; ranking não é teste estatístico.",
        "Suporte por classe pode ser baixo ou zero. Não há promoção automática de champion."
      ]
    }
  end
end
