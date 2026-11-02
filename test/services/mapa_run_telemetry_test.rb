require "test_helper"
class MapaRunTelemetryTest < ActiveSupport::TestCase
  test "summarizes finished and prolonged tasks without state mutation" do
    now = Time.current
    finished = MapaRun.create!(seed: 12, status: "completed",
      started_at: now - 120.seconds, finished_at: now)
    running = MapaRun.create!(seed: 13, status: "running",
      started_at: now - 901.seconds)
    summary = MapaRunTelemetry.summarize([finished, running], now: now)
    assert_equal 120.0, summary[:mean_duration]
    assert_equal 1, summary[:prolonged_count]
    assert_equal "running", running.reload.status
  end
  test "missing timestamps produce no invented duration" do
    run = MapaRun.new(seed: 15, status: "queued")
    assert_nil MapaRunTelemetry.duration_seconds(run)
  end
end
