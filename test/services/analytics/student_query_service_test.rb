require "test_helper"
require "tmpdir"
require "fileutils"

class StudentQueryServiceTest < ActiveSupport::TestCase
  setup do
    @root = Dir.mktmpdir("epa-analytics-test")
    @version = "synthetic-v3-test"
    @dir = File.join(@root, @version)
    FileUtils.mkdir_p(@dir)
    @parquet = File.join(@dir, "period_records.parquet")
    File.binwrite(@parquet, "parquet fixture bytes")
    File.write(File.join(@dir, "manifest.json"), JSON.generate({
      "schema_version" => "epa.genesis.dataset.v3", "classification" => "SYNTHETIC",
      "artifacts" => {
        "period_records" => { "path" => "period_records.parquet",
                              "sha256" => Digest::SHA256.file(@parquet).hexdigest }
      }
    }))
    @service = Analytics::StudentQueryService.new(dataset_root: @root, duckdb_binary: "duckdb")
  end

  teardown { FileUtils.remove_entry_secure(@root) if File.exist?(@root) }

  test "returns a verified aggregated student from separate process output" do
    response = [{ "student_id" => "SYN00000001", "period_records" => 4,
                  "average_grade" => 6.5, "attendance_rate" => 0.95 }].to_json
    status = Struct.new(:success?).new(true)
    called = nil
    Open3.stub(:capture3, ->(*args) { called = args; [response, "", status] }) do
      output = @service.call(student_id: "SYN00000001", dataset_version: @version)
      assert_equal 6.5, output["average_grade"]
      assert_equal "SYNTHETIC", output["data_classification"]
      assert_match(/\ASET memory_limit/, called.last)
      assert_equal ["duckdb", "-json", "-c"], called.first(3)
    end
  end

  test "rejects traversal before starting duckdb" do
    assert_raises(Analytics::StudentQueryService::InvalidRequest) do
      @service.call(student_id: "SYN00000001", dataset_version: "../../etc")
    end
    assert_raises(Analytics::StudentQueryService::InvalidRequest) do
      @service.call(student_id: "SYN00000001'; DROP TABLE x", dataset_version: @version)
    end
  end

  test "rejects tampered parquet before querying" do
    File.binwrite(@parquet, "tampered")
    assert_raises(Analytics::StudentQueryService::DatasetUnavailable) do
      @service.call(student_id: "SYN00000001", dataset_version: @version)
    end
  end
