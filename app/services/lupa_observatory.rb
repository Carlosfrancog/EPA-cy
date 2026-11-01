# Read-only LUPA aggregation of already verified synthetic experiment reports.
class LupaObservatory
  PROTOCOLS = %w[early trajectory consolidated].freeze
  FEATURES = %w[current_mean_grade current_attendance_rate current_absences current_unexcused_absences current_sessions prior_mean_grade prior_attendance_rate prior_absences prior_unexcused_absences prior_term_count prior_years_observed].freeze

  def self.compare(runs, protocol: "early")
    raise ArgumentError, "invalid protocol" unless PROTOCOLS.include?(protocol)
    rows = runs.filter_map do |run|
      next unless run.status == "completed"
      report = run.lupa_report
      next unless report.is_a?(Hash)
      next unless report["schema_version"] == "epa.lupa.explainability.v1"
      next unless report["dataset_classification"] == "SYNTHETIC"
      next unless report["source_manifest_sha256"] == run.dataset_manifest_sha256
      next unless report["seed"] == run.seed
      explanations = report["explanations"]
      next unless explanations.is_a?(Array)
      block = explanations.find { |e| e.is_a?(Hash) && e["protocol"] == protocol }
      next unless block && block["algorithm"] == "random_forest"
      next unless block["importance_method"] == "heldout_permutation_macro_f1"
      features = block["features"]
      next unless features.is_a?(Array) && features.size == FEATURES.size
      next unless features.map { |f| f.is_a?(Hash) ? f["name"] : nil }.sort == FEATURES.sort
      next unless features.all? do |f|
        %w[mean_f1_drop std_f1_drop].all? { |key| f[key].is_a?(Numeric) && f[key].finite? } &&
          f["std_f1_drop"] >= 0
      end
      score = block["baseline_f1_macro"]
      next unless score.is_a?(Numeric) && score.finite? && score.between?(0, 1)
      next unless block["test_observations"].is_a?(Integer) && block["test_observations"] > 0
      { run_id: run.id, seed: run.seed, score: score,
        test_observations: block["test_observations"],
        features: features.sort_by { |f| [-f["mean_f1_drop"], f["name"]] },
        manifest_sha256: report["source_manifest_sha256"] }
    end
    rows.sort_by! { |r| -r[:run_id] }
    { protocol: protocol, rows: rows, total: rows.length,
      warning: "Permutation importance mede sensibilidade de F1 macro, não causalidade. Dados sintéticos não validam eficácia real. Valores negativos são possíveis. Não compare magnitudes entre coortes diferentes como efeito causal." }
  end
end
