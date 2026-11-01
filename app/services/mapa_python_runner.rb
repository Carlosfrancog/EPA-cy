require "json"
require "digest"
require "open3"
require "timeout"
require "fileutils"

class MapaPythonRunner
  class Failure < StandardError
    attr_reader :code
    def initialize(code)
      @code = code
      super(code)
    end
  end

  TIMEOUT_SECONDS = 240
  MAX_REPORT_BYTES = 350_000
  DEMO_STUDENTS = 80

  def initialize(root: Rails.root, python: ENV.fetch("EPA_PYTHON_EXECUTABLE", "python3"))
    @root = Pathname.new(root).realpath
    @python = python
  end

  def call(run)
    dataset = @root.join("data", "mapa-demo-v2")
    ensure_demo_dataset!(dataset)
    output_dir = @root.join("data", "mapa-runs", run.id.to_s)
    FileUtils.mkdir_p(output_dir)
    output = output_dir.join("report.json")
    raise Failure.new("output_already_exists") if output.exist?

    invoke("epa.core_engine.mapa", "--dataset", dataset.to_s,
           "--seed", run.seed.to_s, "--output", output.to_s)
    raise Failure.new("report_missing") unless output.file?
    raise Failure.new("report_too_large") if output.size > MAX_REPORT_BYTES

    raw = output.binread
    report = JSON.parse(raw)
    manifest_sha = Digest::SHA256.file(dataset.join("manifest.json")).hexdigest
    raise Failure.new("report_invalid") unless valid_report?(report, manifest_sha)

    { json: raw, sha256: Digest::SHA256.hexdigest(raw), dataset_sha256: manifest_sha }
  rescue JSON::ParserError
    raise Failure.new("report_invalid")
  end

  private

  def ensure_demo_dataset!(directory)
    if directory.exist?
      raise Failure.new("incomplete_demo_dataset") unless directory.join("manifest.json").file?
      return
    end
    invoke("epa.genesis.v2", "--catalog", @root.join("examples", "atlas.demo.json").to_s,
           "--output", directory.to_s, "--students", DEMO_STUDENTS.to_s, "--seed", "20261029")
    raise Failure.new("dataset_missing") unless directory.join("manifest.json").file?
  end

  def invoke(module_name, *args)
    stdout, stderr, status = Timeout.timeout(TIMEOUT_SECONDS) do
      Open3.capture3({ "PYTHONPATH" => @root.to_s },
                     @python, "-m", module_name, *args, chdir: @root.to_s)
    end
    raise Failure.new("engine_failed") unless status.success?
    raise Failure.new("engine_output_too_large") if stdout.bytesize > 200_000 || stderr.bytesize > 200_000
  rescue Timeout::Error
    raise Failure.new("engine_timeout")
  rescue Errno::ENOENT
    raise Failure.new("python_missing")
  end

  def valid_report?(report, digest)
    return false unless report.is_a?(Hash)
    return false unless report["schema_version"] == "epa.mapa.benchmark.v1"
    return false unless report["dataset_classification"] == "SYNTHETIC"
    return false unless report["research_status"] == "EXPERIMENTAL_NOT_EMPIRICALLY_VALIDATED"
    return false unless report["dataset_manifest_sha256"] == digest
    baselines = report["baselines"]
    return false unless baselines.is_a?(Array) && baselines.map { |b| b["cutoff_term"] } == [1, 2, 3]
    baselines.all? do |block|
      results = block["results"]
      block["classes"] == %w[approved recovery failed] &&
        results.is_a?(Array) && results.map { |r| r["model"] }.sort == %w[logistic_regression majority random_forest] &&
        results.all? do |result|
          %w[accuracy balanced_accuracy f1_macro].all? do |metric|
            value = result[metric]
            value.is_a?(Numeric) && value.finite? && value.between?(0, 1)
          end &&
          result["confusion_matrix"].is_a?(Array) &&
          result["confusion_matrix"].size == 3 &&
          result["confusion_matrix"].all? { |row| row.is_a?(Array) && row.size == 3 && row.all? { |v| v.is_a?(Integer) && v >= 0 } }
        end
    end
  end
end
