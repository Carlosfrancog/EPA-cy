# Descriptive, paired comparison of identical synthetic GroupKFold test folds.
# No hypothesis testing, population CI, or champion promotion.
class MapaPairedComparison
  MODELS = %w[majority logistic_regression random_forest mlp xgboost].freeze
  PROTOCOLS = %w[early trajectory consolidated].freeze

  def self.build(run, protocol:, reference: "majority")
    raise ArgumentError, "invalid protocol" unless PROTOCOLS.include?(protocol)
    raise ArgumentError, "invalid reference" unless MODELS.include?(reference)

    baseline = run.research_report
    extended = run.research_extended_report
    return unavailable("missing_reports") unless valid_header?(baseline, run, "epa.mapa.research_protocol.v2") &&
                                                  valid_header?(extended, run, "epa.mapa.research_extended.v1")
    b = baseline.fetch("protocols", []).find { |p| p.is_a?(Hash) && p["protocol"] == protocol }
    e = extended.fetch("protocols", []).find { |p| p.is_a?(Hash) && p["protocol"] == protocol }
    return unavailable("protocol_missing") unless b && e
    return unavailable("fold_strategy_mismatch") unless b["fold_strategy"] == "GroupKFold_by_student" &&
                                                        e["fold_strategy"] == "GroupKFold_by_student" &&
                                                        b["n_splits"] == e["n_splits"] &&
                                                        b["n_splits"].is_a?(Integer) && b["n_splits"] >= 2

    by_model = {}
    (b.fetch("folds", []) + e.fetch("folds", [])).each do |fold|
      next unless fold.is_a?(Hash) && MODELS.include?(fold["model"])
      next if fold["status"] == "skipped"
      score = fold["f1_macro"]
      index = fold["fold"]
      next unless score.is_a?(Numeric) && score.finite? && score.between?(0, 1)
      next unless index.is_a?(Integer) && index.between?(1, b["n_splits"])
      next unless fold["test_students"].is_a?(Integer) && fold["test_students"] > 0
      next unless fold["train_students"].is_a?(Integer) && fold["train_students"] > 0
      support = fold["class_support"]
      next unless support.is_a?(Hash) && %w[approved recovery failed].all? { |c| support[c].is_a?(Integer) && support[c] >= 0 }
      next if by_model.fetch(fold["model"], {}).key?(index)
      (by_model[fold["model"]] ||= {})[index] = fold
    end

    reference_folds = by_model.fetch(reference, {})
    return unavailable("reference_not_complete") unless reference_folds.length == b["n_splits"]
    rows = MODELS.filter_map do |name|
      candidate_folds = by_model.fetch(name, {})
      next unless candidate_folds.length == b["n_splits"]
      paired = (1..b["n_splits"]).map do |i|
        a, z = candidate_folds[i], reference_folds[i]
        next unless a && z && a["train_students"] == z["train_students"] &&
                    a["test_students"] == z["test_students"] &&
                    a["class_support"] == z["class_support"]
        a["f1_macro"] - z["f1_macro"]
      end
      next if paired.any?(&:nil?)
      { model: name, mean_f1_delta: paired.sum / paired.length.to_f,
        min_f1_delta: paired.min, max_f1_delta: paired.max,
        wins: paired.count { |delta| delta > 1e-12 },
        ties: paired.count { |delta| delta.abs <= 1e-12 },
        losses: paired.count { |delta| delta < -1e-12 },
        paired_folds: paired.length }
    end
    { status: "descriptive", protocol: protocol, reference: reference,
      rows: rows.sort_by { |row| [-row[:mean_f1_delta], row[:model]] },
      folds: b["n_splits"],
      caveat: "Diferenças pareadas de F1 macro em folds sintéticos agrupados por estudante. Não representam teste de significância, intervalo de confiança, efeito causal ou validação externa." }
  end

  def self.valid_header?(report, run, schema)
    report.is_a?(Hash) && report["schema_version"] == schema &&
      report["dataset_classification"] == "SYNTHETIC" &&
      report["research_status"] == "EXPERIMENTAL_NOT_EMPIRICALLY_VALIDATED" &&
      report["source_manifest_sha256"] == run.dataset_manifest_sha256 &&
      report["seed"] == run.seed
  end
  private_class_method :valid_header?

  def self.unavailable(reason)
    { status: "unavailable", reason: reason, rows: [] }
  end
  private_class_method :unavailable
end
