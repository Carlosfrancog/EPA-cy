require "test_helper"
class MapaEvidenceGatesTest < ActiveSupport::TestCase
  def fake_run(with_research: true)
    hash = {schema_version: "epa.mapa.research_protocol.v2", dataset_classification: "SYNTHETIC",
      source_manifest_sha256: "a" * 64, seed: 33,
      protocols: [{protocol: "early", summaries: [{model: "random_forest",
        missing_class_folds: 0, f1_macro_fold_distribution: {mean: 0.7, min: 0.6, max: 0.8, std: 0.1, n_folds: 3}}],
        temporal_holdout: {status: "evaluated", models: [{model: "random_forest"}]}}]}
    MapaRun.create!(seed: 33, status: "completed", dataset_manifest_sha256: "a" * 64,
                    research_json: with_research ? hash.to_json : nil)
  end

  test "synthetic evidence never unlocks deployment" do
    result = MapaEvidenceGates.assess(fake_run, protocol: "early", model: "random_forest")
    assert_equal "research_only", result[:status]
    assert_equal false, result[:deployable]
    assert_match(/dados exclusivamente sintéticos/i, result[:reasons].join(" "))
    assert_equal 0.7, result[:cv_f1_mean]
  end

  test "missing research is explicitly insufficient" do
    result = MapaEvidenceGates.assess(fake_run(with_research: false), protocol: "early", model: "random_forest")
    assert_equal "insufficient_evidence", result[:status]
  end

  test "tampered provenance cannot pass" do
    run = fake_run
    run.update!(dataset_manifest_sha256: "b" * 64)
    assert_equal "insufficient_evidence", MapaEvidenceGates.assess(run, protocol: "early", model: "random_forest")[:status]
  end
end
