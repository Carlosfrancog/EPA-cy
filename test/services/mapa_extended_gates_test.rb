require "test_helper"
class MapaExtendedGatesTest < ActiveSupport::TestCase
  test "extended model reads its own grouped research and remains research-only" do
    research = {schema_version: "epa.mapa.research_extended.v1",
      dataset_classification: "SYNTHETIC", source_manifest_sha256: "a" * 64,
      seed: 19, protocols: [{protocol: "early",
        summaries: [{model: "mlp", status: "evaluated", missing_class_folds: 0,
          f1_macro_fold_distribution: {mean: 0.6, std: 0.1, min: 0.5, max: 0.7, n_folds: 3}}],
        temporal_holdout: {status: "not_identifiable", reason: "same_students_across_years"}}]}
    run = MapaRun.create!(seed: 19, status: "completed",
      dataset_manifest_sha256: "a" * 64, research_extended_json: research.to_json)
    result = MapaEvidenceGates.assess(run, protocol: "early", model: "mlp")
    assert_equal "research_only", result[:status]
    assert_equal false, result[:deployable]
    assert_equal 0.6, result[:cv_f1_mean]
    assert_match(/temporal/i, result[:reasons].join(" "))
    run.update!(dataset_manifest_sha256: "b" * 64)
    assert_equal "insufficient_evidence", MapaEvidenceGates.assess(run, protocol: "early", model: "mlp")[:status]
  end
end
