require "open3"
require "timeout"
require "digest"
require "json"
require "fileutils"

# Explicitly bounded local Python bridge. NOT a sandbox or distributed job queue.
# Users cannot submit executable paths, module names, arguments or arbitrary files.
class EpaPythonRunner
  class Failure < StandardError
    attr_reader :code

    def initialize(code)
      @code = code
      super(code)
    end
  end

  TIMEOUT_SECONDS = 180
  MAX_REPORT_BYTES = 100_000

  def initialize(root: Rails.root, python: ENV.fetch("EPA_PYTHON_EXECUTABLE", "python3"))
    @root = Pathname.new(root).realpath
    @python = python
  end

  def call(run)
    ensure_demo_dataset!
    output_directory = @root.join("data", "runs", run.id.to_s)
    FileUtils.mkdir_p(output_directory)
    output_path = output_directory.join("report.json")
    raise Failure, "output_already_exists" if output_path.exist?

    dataset = @root.join("data", "demo", "academic_history.parquet")
    invoke_module("epa.core_engine.cli", "--dataset", dataset.to_s,
                  "--seed", run.seed.to_s, "--output", output_path.to_s)
    raise Failure, "report_not_created" unless output_path.file?
    raise Failure, "report_too_large" if output_path.size > MAX_REPORT_BYTES

    raw = output_path.binread
    report = JSON.parse(raw)
    raise Failure, "report_invalid" unless valid_report?(report, dataset)
    { json: raw, sha256: Digest::SHA256.hexdigest(raw),
      input_sha256: report.fetch("input_sha256") }
  rescue JSON::ParserError, KeyError
    raise Failure, "report_invalid"
  end

  private

  def ensure_demo_dataset!
    directory = @root.join("data", "demo")
    dataset = directory.join("academic_history.parquet")
    manifest = directory.join("manifest.json")
    return if dataset.file? && manifest.file?
    raise Failure, "incomplete_demo_dataset" if directory.exist?

    invoke_module("epa.genesis.generate",
                  "--catalog", @root.join("examples", "atlas.demo.json").to_s,
                  "--output", directory.to_s,
                  "--students", "500",
                  "--seed", "20261029")
    raise Failure, "dataset_not_created" unless dataset.file? && manifest.file?
  end

  def invoke_module(module_name, *args)
    # Module names are hardcoded by the application, never taken from a request.
    env = { "PYTHONPATH" => @root.to_s }
    out, err, status = Timeout.timeout(TIMEOUT_SECONDS) do
      Open3.capture3(env, @python, "-m", module_name, *args, chdir: @root.to_s)
    end
    raise Failure, "engine_failed" unless status.success?
    raise Failure, "engine_output_too_large" if out.bytesize > 200_000 || err.bytesize > 200_000
  rescue Timeout::Error
    raise Failure, "engine_timeout"
  rescue Errno::ENOENT
    raise Failure, "python_missing"
  end

  def valid_report?(report, dataset)
    return false unless report.is_a?(Hash)
    return false unless report["schema_version"] == "epa.core_engine.report.v1"
    return false unless report["dataset_kind"] == "SYNTHETIC"
    return false unless report["research_status"] == "EXPERIMENTAL_NOT_VALIDATED"
    return false unless report["input_sha256"] == Digest::SHA256.file(dataset).hexdigest
    return false unless report["results"].is_a?(Array) && report["results"].size == 3
    models = report["results"].map { |r| r.is_a?(Hash) ? r["model"] : nil }
    return false unless models.sort == ExperimentRun::MODELS.keys.sort
    report["results"].all? do |entry|
      %w[accuracy balanced_accuracy f1_macro].all? do |metric|
        value = entry[metric]
        value.is_a?(Numeric) && value.finite? && value.between?(0, 1)
      end
    end
  end
end
