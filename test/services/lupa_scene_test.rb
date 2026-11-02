require "test_helper"
class LupaSceneTest < ActiveSupport::TestCase
  test "does not invent a scene when only partial evidence exists" do
    run = MapaRun.create!(seed: 15, status: "completed", dataset_manifest_sha256: "a" * 64)
    assert_nil LupaScene.for_run(run)
  end

  test "constructs scene only from three validated protocols" do
    features = LupaObservatory::FEATURES.map do |name|
      {name: name, mean_f1_drop: -0.012, std_f1_drop: 0.004}
    end
    explanations = %w[early trajectory consolidated].each_with_index.map do |protocol, index|
      {protocol: protocol, cutoff_term: index + 1, algorithm: "random_forest",
       importance_method: "heldout_permutation_macro_f1",
       baseline_f1_macro: 0.65, test_observations: 12, features: features}
    end
    run = MapaRun.create!(seed: 15, status: "completed", dataset_manifest_sha256: "a" * 64,
      lupa_json: {schema_version: "epa.lupa.explainability.v1",
        dataset_classification: "SYNTHETIC", source_manifest_sha256: "a" * 64,
        seed: 15, explanations: explanations}.to_json)
    scene = LupaScene.for_run(run)
    assert_equal 3, scene[:protocols].size
    assert_equal 33, scene[:protocols].sum { |p| p[:features].size }
    assert_equal(-0.012, scene[:protocols][0][:features][0][:importance])
    run.update!(dataset_manifest_sha256: "b" * 64)
    assert_nil LupaScene.for_run(run)
  end
end
