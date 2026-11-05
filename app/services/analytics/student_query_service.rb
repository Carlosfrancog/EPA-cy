# frozen_string_literal: true

require "json"
require "digest"
require "open3"
require "pathname"
require "timeout"

module Analytics
  # Executes one read-only, bounded aggregation in a separate DuckDB CLI process.
  # Expects immutable GENESIS v3 datasets under data/datasets/<dataset_version>/.
  # It does NOT load the student history into ActiveRecord or the Rails process.
  class StudentQueryService
    class InvalidRequest < StandardError; end
    class DatasetUnavailable < StandardError; end
    class StudentNotFound < StandardError; end
    class QueryFailed < StandardError; end

    STUDENT_ID_FORMAT = /\ASYN\d{8}\z/
    VERSION_FORMAT = /\A[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}\z/
    SHA256_FORMAT = /\A[0-9a-f]{64}\z/
    TIMEOUT_SECONDS = 20
    OUTPUT_LIMIT = 16_384
    DATASET_SCHEMA = "epa.genesis.dataset.v3"

    def initialize(dataset_root: Rails.root.join("data", "datasets"),
                   duckdb_binary: ENV.fetch("EPA_DUCKDB_CLI", "duckdb"), command_runner: Open3)
      @dataset_root = Pathname.new(dataset_root)
      @duckdb_binary = duckdb_binary
      @command_runner = command_runner
    end

    def call(student_id:, dataset_version:)
      student_id = student_id.to_s
      dataset_version = dataset_version.to_s
      raise InvalidRequest, "invalid student_id" unless STUDENT_ID_FORMAT.match?(student_id)
      raise InvalidRequest, "invalid dataset_version" unless VERSION_FORMAT.match?(dataset_version)

      parquet_path, manifest_sha = verified_dataset(dataset_version)
      # Only a fixed query is permitted. Inputs are constrained before quoting.
      # The complete file path is generated server-side and SQL-quoted.
      sql = <<~SQL
        SET memory_limit = '512MB';
        SET threads = 2;
        SELECT
          student_id,
          COUNT(*) AS period_records,
          COUNT(DISTINCT academic_year) AS academic_years,
          ROUND(AVG(assessment_grade), 4) AS average_grade,
          SUM(scheduled_sessions) AS scheduled_sessions,
          SUM(present_sessions) AS present_sessions,
          ROUND(SUM(present_sessions) * 1.0 / NULLIF(SUM(scheduled_sessions), 0), 6) AS attendance_rate,
          SUM(absences_unexcused) AS unexcused_absences
        FROM read_parquet('#{quote_sql(parquet_path.to_s)}')
        WHERE student_id = '#{student_id}'
        GROUP BY student_id;
      SQL

      stdout, stderr, status = Timeout.timeout(TIMEOUT_SECONDS) do
        @command_runner.capture3(@duckdb_binary, "-json", "-c", sql)
      end
      raise QueryFailed, "duckdb returned non-zero exit status" unless status.success?
      raise QueryFailed, "duckdb stdout too large" if stdout.bytesize > OUTPUT_LIMIT
      raise QueryFailed, "duckdb stderr too large" if stderr.bytesize > OUTPUT_LIMIT

      rows = JSON.parse(stdout)
      raise QueryFailed, "unexpected duckdb result" unless rows.is_a?(Array) && rows.size <= 1
      raise StudentNotFound, "student not found" if rows.empty?
      row = rows.fetch(0)
      raise QueryFailed, "unexpected student_id in result" unless row.is_a?(Hash) && row["student_id"] == student_id
      row.merge("dataset_version" => dataset_version, "manifest_sha256" => manifest_sha,
                "data_classification" => "SYNTHETIC")
    rescue Timeout::Error
      raise QueryFailed, "duckdb query timed out"
    rescue Errno::ENOENT
      raise QueryFailed, "duckdb CLI not found"
    rescue JSON::ParserError
      raise QueryFailed, "invalid duckdb JSON response"
    end

    private

    def verified_dataset(dataset_version)
      root = @dataset_root.realpath
      dir = (root / dataset_version).realpath
      # Reject traversal through symlinks even when the version string is valid.
      raise DatasetUnavailable, "dataset escapes configured root" unless dir.dirname == root
      raise DatasetUnavailable, "dataset is not a directory" unless dir.directory?

      manifest_path = dir / "manifest.json"
      raise DatasetUnavailable, "manifest missing" unless manifest_path.file?
      manifest = JSON.parse(manifest_path.read)
      raise DatasetUnavailable, "unsupported manifest" unless manifest.is_a?(Hash) &&
        manifest["schema_version"] == DATASET_SCHEMA && manifest["classification"] == "SYNTHETIC"

      artifact = manifest.fetch("artifacts").fetch("period_records")
      raise DatasetUnavailable, "invalid artifact path" unless artifact.is_a?(Hash) &&
        artifact["path"] == "period_records.parquet" &&
        SHA256_FORMAT.match?(artifact["sha256"].to_s)

      file = (dir / "period_records.parquet").realpath
      raise DatasetUnavailable, "artifact escapes dataset" unless file.dirname == dir && file.file?
      # MVP fail-closed verification. O(file size) per request: replace only with
      # an immutable, trusted verification registry in a subsequent iteration.
      raise DatasetUnavailable, "artifact SHA-256 mismatch" unless
        Digest::SHA256.file(file).hexdigest == artifact["sha256"]
      [file, Digest::SHA256.file(manifest_path).hexdigest]
    rescue Errno::ENOENT, Errno::EACCES, JSON::ParserError, KeyError, TypeError
      raise DatasetUnavailable, "dataset is missing or malformed"
    end

    def quote_sql(string)
      string.gsub("'", "''")
    end
  end
end
