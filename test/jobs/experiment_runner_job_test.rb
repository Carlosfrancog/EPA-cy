require "test_helper"
require "minitest/mock"

class ExperimentRunnerJobTest < ActiveJob::TestCase
  test "finished worker stores real report and digests" do
    run = ExperimentRun.create!(model_key: "random_forest", seed: 42, status: "queued")
    report = {
      schema_version: "epa.core_engine.report.v1",
      dataset_kind: "SYNTHETIC",
      research_status: "EXPERIMENTAL_NOT_VALIDATED",
      results: []
    }.to_json
    evidence = {json: report, sha256: "a" * 64, input_sha256: "b" * 64}
    fake = Object.new
    fake.define_singleton_method(:call) { |_run| evidence }
    EpaPythonRunner.stub(:new, fake) { ExperimentRunnerJob.perform_now(run.id) }
    run.reload
    assert_equal "completed", run.status
    assert_equal report, run.report_json
    assert_equal "a" * 64, run.report_sha256
  end

  test "duplicate delivery does not rerun experiment" do
    run = ExperimentRun.create!(model_key: "majority", seed: 42, status: "completed")
    EpaPythonRunner.stub(:new, -> { flunk("runner should not initialize") }) do
      ExperimentRunnerJob.perform_now(run.id)
    end
    assert_equal "completed", run.reload.status
  end

  test "bridge failure marks job failed without publishing results" do
    run = ExperimentRun.create!(model_key: "majority", seed: 42, status: "queued")
    fake = Object.new
    fake.define_singleton_method(:call) { |_run| raise EpaPythonRunner::Failure, "python_missing" }
    EpaPythonRunner.stub(:new, fake) { ExperimentRunnerJob.perform_now(run.id) }
    run.reload
    assert_equal "failed", run.status
    assert_equal "python_missing", run.failure_code
    assert_nil run.report_json
  end
end
