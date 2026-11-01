require "test_helper"

class MapaRunnerJobTest < ActiveJob::TestCase
  test "worker persists verified payload without reprocessing" do
    run = MapaRun.create!(seed: 123)
    evidence = { json: '{"schema_version":"epa.mapa.benchmark.v1"}',
                 sha256: "a" * 64, dataset_sha256: "b" * 64 }
    fake = Object.new
    fake.define_singleton_method(:call) { |_run| evidence }
    job = MapaRunnerJob.new
    job.define_singleton_method(:runner) { fake }
    job.perform(run.id)
    assert_equal "completed", run.reload.status
    assert_equal "b" * 64, run.dataset_manifest_sha256
    job.perform(run.id)
    assert_equal "completed", run.reload.status
  end

  test "controlled python failure is persisted" do
    run = MapaRun.create!(seed: 12)
    fake = Object.new
    fake.define_singleton_method(:call) { |_run| raise MapaPythonRunner::Failure.new("engine_failed") }
    job = MapaRunnerJob.new
    job.define_singleton_method(:runner) { fake }
    job.perform(run.id)
    assert_equal "failed", run.reload.status
    assert_equal "engine_failed", run.failure_code
    assert_nil run.report_json
  end
end
