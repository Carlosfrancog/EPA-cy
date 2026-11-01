require "test_helper"

class MapaPythonRunnerTest < ActiveSupport::TestCase
  test "validates a genuine MAPA-shaped report" do
    runner = MapaPythonRunner.new
    result = { "model" => "majority", "accuracy" => 0.3, "balanced_accuracy" => 0.3,
               "f1_macro" => 0.2, "confusion_matrix" => [[1, 0, 0], [1, 0, 0], [1, 0, 0]] }
    report = { "schema_version" => "epa.mapa.benchmark.v1",
               "dataset_classification" => "SYNTHETIC",
               "research_status" => "EXPERIMENTAL_NOT_EMPIRICALLY_VALIDATED",
               "dataset_manifest_sha256" => "a" * 64,
               "baselines" => [1, 2, 3].map { |i|
                 { "cutoff_term" => i, "classes" => %w[approved recovery failed],
                   "results" => %w[majority logistic_regression random_forest].map { |m| result.merge("model" => m) } }
               } }
    assert runner.send(:valid_report?, report, "a" * 64)
    report["baselines"][0]["results"][0]["confusion_matrix"] = [[1, 2], [2, 1]]
    refute runner.send(:valid_report?, report, "a" * 64)
  end
end
