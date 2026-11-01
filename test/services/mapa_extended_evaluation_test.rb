require "test_helper"
class MapaExtendedEvaluationTest < ActiveSupport::TestCase
  test "extended results with verified source appear in ranking" do
    run = MapaRun.create!(seed: 42, status: "completed", dataset_manifest_sha256: "a" * 64,
      report_json: {schema_version: "epa.mapa.benchmark.v1", dataset_classification: "SYNTHETIC",
        baselines: [{protocol: "early", test_class_counts: {approved: 6, recovery: 3, failed: 1}, results: []}]}.to_json,
      extended_json: {schema_version: "epa.mapa.extended_models.v1", dataset_classification: "SYNTHETIC",
        source_manifest_sha256: "a" * 64, protocols: [{protocol: "early", seed: 42,
        results: [{model: "mlp", status: "evaluated", f1_macro: 0.6, accuracy: 0.6,
          balanced_accuracy: 0.6, recall_by_class: {approved: 0.7, recovery: 0.5, failed: 0.5}}]}]}.to_json)
    assert_equal ["mlp"], MapaEvaluation.build([run], model: "mlp")[:rows].map { |v| v[:model] }
    run.update!(dataset_manifest_sha256: "b" * 64)
    assert_empty MapaEvaluation.build([run], model: "mlp")[:rows]
  end
end
