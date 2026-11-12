require "test_helper"
require "tmpdir"

class NativeMapaRunsTest < ActionDispatch::IntegrationTest
  include ActiveJob::TestHelper

  test "native lab page is navigable" do
    get native_mapa_runs_path
    assert_response :success
    assert_select "h1", text: "Laboratório Visual MAPA"
    assert_select "form[action='#{native_mapa_runs_path}']"
  end

  test "invalid dataset cannot enqueue any job" do
    assert_no_difference("NativeMapaRun.count") do
      assert_no_enqueued_jobs do
        post native_mapa_runs_path, params: {
          dataset_key: "../../etc", seed: "42", max_students: "500",
          models: %w[majority logistic_regression]
        }
      end
    end
    assert_redirected_to native_mapa_runs_path
  end

  test "recognized synthetic manifest queues one job" do
    directory = Rails.root.join("data", "mapa-features-rails-test")
    FileUtils.mkdir_p(directory)
    directory.join("manifest.json").write({
      schema_version: "epa.mapa.feature_dataset.v1",
      classification: "SYNTHETIC"
    }.to_json)
    begin
      assert_difference("NativeMapaRun.count", 1) do
        assert_enqueued_with(job: NativeMapaRunnerJob) do
          post native_mapa_runs_path, params: {
            dataset_key: directory.basename.to_s,
            seed: "42", max_students: "500",
            models: %w[majority mlp]
          }
        end
      end
      assert_redirected_to native_mapa_run_path(NativeMapaRun.order(:id).last)
    ensure
      FileUtils.remove_entry(directory) if directory.directory?
    end
  end

  test "run visualizes measured results without inventing epochs" do
    run = NativeMapaRun.create!(
      seed: 42, max_students: 500,
      dataset_key: "mapa-features-example",
      model_keys_json: %w[majority].to_json,
      status: "completed",
      report_json: {
        schema_version: "epa.mapa.native_training.v1",
        feature_manifest_sha256: "a" * 64,
        classes: %w[approved recovery failed],
        protocols: (1..3).map { |cutoff|
          { cutoff_term: cutoff, test_observations: 12,
            results: [{ model: "majority", f1_macro: 0.2, log_loss: 0.8,
                        brier_multiclass: 0.5, fit_seconds: 0.01,
                        recall_by_class: { failed: 0.0 },
                        confusion_matrix: [[4,0,0],[4,0,0],[4,0,0]] }] }
        }
      }.to_json
    )
    get native_mapa_run_path(run)
    assert_response :success
    assert_select "[data-native-timeline]"
    assert_select "svg.native-network", 0
    assert_select "body", /Timelapse dos cortes acadêmicos/
  end
end
