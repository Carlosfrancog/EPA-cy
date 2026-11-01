require "test_helper"

class MapaEvaluationTest < ActiveSupport::TestCase
  def create_run(score, model = "random_forest")
    MapaRun.create!(status: "completed", seed: 42,
      dataset_manifest_sha256: "a" * 64,
      report_json: {
        schema_version: "epa.mapa.benchmark.v1", dataset_classification: "SYNTHETIC",
        baselines: [{ protocol: "early", test_class_counts: {approved: 6, recovery: 3, failed: 1},
          results: [{ model: model, f1_macro: score, accuracy: 0.6, balanced_accuracy: 0.4,
                      recall_by_class: {approved: 0.8, recovery: 0.3, failed: 0.0} }] }]
      }.to_json)
  end

  test "ranks results and reports candidates without promoting models" do
    low = create_run(0.25)
    high = create_run(0.65)
    result = MapaEvaluation.build([low, high])
    assert_equal [high.id, low.id], result[:rows].map { |x| x[:run_id] }
    assert_equal high.id, result[:best_per_model].first[:run_id]
    assert_equal 2, result[:evaluated_runs]
    assert_match(/não há promoção automática/i, result[:warnings].join(" "))
  end

  test "model filter and invalid options" do
    create_run(0.5)
    assert_empty MapaEvaluation.build(MapaRun.all, model: "majority")[:rows]
    assert_raises(ArgumentError) { MapaEvaluation.build([], protocol: "future") }
  end
end
