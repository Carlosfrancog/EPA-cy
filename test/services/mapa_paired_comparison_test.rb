require "test_helper"

class MapaPairedComparisonTest < ActiveSupport::TestCase
  def run_with_folds
    baseline_folds = [1, 2, 3].map do |i|
      {fold: i, model: "majority", f1_macro: 0.3, train_students: 20,
       test_students: 10, class_support: {approved: 5, recovery: 3, failed: 2}}
    end
    extended_folds = [1, 2, 3].map do |i|
      {fold: i, model: "mlp", f1_macro: 0.4 + i * 0.01,
       train_students: 20, test_students: 10,
       class_support: {approved: 5, recovery: 3, failed: 2}}
    end
    common = {dataset_classification: "SYNTHETIC",
      research_status: "EXPERIMENTAL_NOT_EMPIRICALLY_VALIDATED",
      source_manifest_sha256: "a" * 64, seed: 42}
    MapaRun.create!(seed: 42, status: "completed", dataset_manifest_sha256: "a" * 64,
      research_json: common.merge(schema_version: "epa.mapa.research_protocol.v2",
        protocols: [{protocol: "early", fold_strategy: "GroupKFold_by_student",
          n_splits: 3, folds: baseline_folds}]).to_json,
      research_extended_json: common.merge(schema_version: "epa.mapa.research_extended.v1",
        protocols: [{protocol: "early", fold_strategy: "GroupKFold_by_student",
          n_splits: 3, folds: extended_folds}]).to_json)
  end

  test "compares aligned folds without promoting models" do
    result = MapaPairedComparison.build(run_with_folds, protocol: "early")
    assert_equal "descriptive", result[:status]
    mlp = result[:rows].find { |row| row[:model] == "mlp" }
    assert_equal 3, mlp[:wins]
    assert_in_delta 0.12, mlp[:mean_f1_delta], 0.00001
  end

  test "does not compare different class support" do
    run = run_with_folds
    report = run.research_extended_report
    report["protocols"][0]["folds"][0]["class_support"]["approved"] = 4
    run.update!(research_extended_json: report.to_json)
    result = MapaPairedComparison.build(run, protocol: "early")
    assert_nil result[:rows].find { |row| row[:model] == "mlp" }
  end

  test "rejects mismatched provenance" do
    run = run_with_folds
    run.update!(dataset_manifest_sha256: "b" * 64)
    assert_equal "unavailable", MapaPairedComparison.build(run, protocol: "early")[:status]
  end
end
