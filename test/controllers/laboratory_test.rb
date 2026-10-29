require "test_helper"

class LaboratoryTest < ActionDispatch::IntegrationTest
  include ActiveJob::TestHelper

  test "create experiment records run and queues worker" do
    assert_difference("ExperimentRun.count", 1) do
      assert_enqueued_with(job: ExperimentRunnerJob) do
        post experiments_path, params: {model: "random_forest", seed: "42"}
      end
    end
    assert_response :see_other
    run = ExperimentRun.order(:id).last
    assert_equal "queued", run.status
    assert_redirected_to experiment_path(run)
  end

  test "rejects unexpected executable model and seed" do
    assert_no_difference("ExperimentRun.count") do
      post experiments_path, params: { model: "python -c 'print(1)'", seed: "42" }
    end
    assert_redirected_to experiments_path
    assert_no_difference("ExperimentRun.count") do
      post experiments_path, params: { model: "majority", seed: "abc" }
    end
  end

  test "shows measured synthetic report without fabricating metrics" do
    run = ExperimentRun.create!(model_key: "majority", seed: 42, status: "completed",
                                report_json: {
                                  schema_version: "epa.core_engine.report.v1",
                                  results: [
                                    {model: "majority", accuracy: 0.5, balanced_accuracy: 0.5,
                                     f1_macro: 0.4, confusion_matrix: [[2, 0], [2, 0]]}
                                  ],
                                  train_observations: 5, test_observations: 4
                                }.to_json,
                                input_sha256: "a" * 64, report_sha256: "b" * 64)
    get experiment_path(run)
    assert_response :success
    assert_select "body", /50,0%|50.0%/
    assert_select "body", /EXPERIMENTAL/
  end

  test "waiting experiment shows status instead of invented scores" do
    run = ExperimentRun.create!(model_key: "random_forest", seed: 42, status: "queued")
    get experiment_path(run)
    assert_response :success
    assert_select "body", /em fila|na fila/
    assert_select "meta[http-equiv=refresh]"
  end
end
