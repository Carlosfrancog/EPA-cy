require "test_helper"
class LupaObservatoryTest < ActiveSupport::TestCase
  test "filters report validity and preserves negative importance" do
    feature_names = LupaObservatory::FEATURES
    run = MapaRun.create!(seed: 42, status: "completed", dataset_manifest_sha256: "a" * 64,
      lupa_json: {schema_version: "epa.lupa.explainability.v1", dataset_classification: "SYNTHETIC",
        seed: 42, source_manifest_sha256: "a" * 64,
        explanations: [{protocol: "early", algorithm: "random_forest",
          importance_method: "heldout_permutation_macro_f1", baseline_f1_macro: 0.5,
          test_observations: 10, features: feature_names.each_with_index.map { |name, i|
            {name: name, mean_f1_drop: i == 0 ? -0.01 : 0.01, std_f1_drop: 0.02} }}]}.to_json)
    result = LupaObservatory.compare([run])
    assert_equal 1, result[:total]
    assert_equal(-0.01, result[:rows].first[:features].last["mean_f1_drop"])
    assert_empty LupaObservatory.compare([run], protocol: "trajectory")[:rows]
    run.update!(dataset_manifest_sha256: "b" * 64)
    assert_empty LupaObservatory.compare([run])[:rows]
  end
end
