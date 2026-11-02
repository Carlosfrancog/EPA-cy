require "test_helper"
class MapaIntegrityAuditTest < ActiveSupport::TestCase
  test "verifies bound report bytes and detects tampering" do
    raw = {schema_version: "epa.mapa.benchmark.v1", dataset_classification: "SYNTHETIC",
           dataset_manifest_sha256: "a" * 64}.to_json
    run = MapaRun.create!(seed: 20, status: "completed", dataset_manifest_sha256: "a" * 64,
                          report_json: raw, report_sha256: Digest::SHA256.hexdigest(raw))
    result = MapaIntegrityAudit.inspect_run(run)
    assert_equal 1, result[:verified]
    assert_equal 0, result[:invalid]
    run.update!(report_json: raw + " ")
    assert_equal 1, MapaIntegrityAudit.inspect_run(run)[:invalid]
  end

  test "missing historical artifacts are not failures" do
    run = MapaRun.create!(seed: 20, status: "completed")
    result = MapaIntegrityAudit.inspect_run(run)
    assert_equal 6, result[:absent]
    assert_equal 0, result[:invalid]
  end
end
