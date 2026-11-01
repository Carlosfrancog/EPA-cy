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

    arguments = ["--dataset", dataset.to_s, "--seed", run.seed.to_s, "--output", output.to_s]
    tracking_enabled = ENV["EPA_MLFLOW_TRACKING_URI"].present?
    links_path = output_dir.join("mlflow-links.json")
    if tracking_enabled
      arguments += ["--mlflow-uri", ENV.fetch("EPA_MLFLOW_TRACKING_URI"),
                    "--mlflow-link-output", links_path.to_s]
    end
    invoke("epa.core_engine.mapa", *arguments)
    raise Failure.new("report_missing") unless output.file?
    raise Failure.new("report_too_large") if output.size > MAX_REPORT_BYTES

    raw = output.binread
    report = JSON.parse(raw)
    manifest_sha = Digest::SHA256.file(dataset.join("manifest.json")).hexdigest
    raise Failure.new("report_invalid") unless valid_report?(report, manifest_sha)

    report_sha = Digest::SHA256.hexdigest(raw)
    links_json = tracking_enabled ? verified_links!(links_path, report, report_sha) : nil
    research_output = output_dir.join("research.json")
    invoke("epa.core_engine.mapa_research", "--dataset", dataset.to_s,
           "--seed", run.seed.to_s, "--folds", "3", "--output", research_output.to_s)
    raise Failure.new("research_report_missing") unless research_output.file?
    raise Failure.new("research_report_too_large") if research_output.size > 900_000
    research_raw = research_output.binread
    research = JSON.parse(research_raw)
    valid_research = research["schema_version"] == "epa.mapa.research_protocol.v2" &&
                     research["dataset_classification"] == "SYNTHETIC" &&
                     research["source_manifest_sha256"] == manifest_sha &&
                     research["protocols"].is_a?(Array) &&
                     research["protocols"].map { |p| p["cutoff_term"] } == [1, 2, 3]
    raise Failure.new("research_report_invalid") unless valid_research
    lupa_output = output_dir.join("lupa.json")
    invoke("epa.core_engine.lupa", "--dataset", dataset.to_s,
           "--seed", run.seed.to_s, "--repeats", "2", "--output", lupa_output.to_s)
    raise Failure.new("lupa_report_missing") unless lupa_output.file?
    raise Failure.new("lupa_report_too_large") if lupa_output.size > 150_000
    lupa_raw = lupa_output.binread
    lupa = JSON.parse(lupa_raw)
    valid_lupa = lupa["schema_version"] == "epa.lupa.explainability.v1" &&
                 lupa["dataset_classification"] == "SYNTHETIC" &&
                 lupa["source_manifest_sha256"] == manifest_sha &&
                 lupa["seed"] == run.seed &&
                 lupa["explanations"].is_a?(Array) &&
                 lupa["explanations"].map { |e| e["cutoff_term"] } == [1, 2, 3] &&
                 lupa["explanations"].all? do |e|
                   e["algorithm"] == "random_forest" && e["features"].is_a?(Array) &&
                     e["features"].size == 11 &&
                     e["features"].all? { |f| f["mean_f1_drop"].is_a?(Numeric) && f["mean_f1_drop"].finite? }
                 end
    raise Failure.new("lupa_report_invalid") unless valid_lupa
    { json: raw, sha256: report_sha, dataset_sha256: manifest_sha,
      lupa_json: lupa_raw, lupa_sha256: Digest::SHA256.hexdigest(lupa_raw),
      mlflow_links_json: links_json, research_json: research_raw,
      research_sha256: Digest::SHA256.hexdigest(research_raw) }
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

  def verified_links!(path, report, sha)
    raise Failure.new("mlflow_links_missing") unless path.file?
    raise Failure.new("mlflow_links_invalid") if path.size > 30_000
    links = JSON.parse(path.binread)
    expected = report.fetch("baselines").flat_map do |block|
      block.fetch("results").map { |result| [block.fetch("protocol"), result.fetch("model")] }
    end
    runs = links["runs"]
    valid = links["schema_version"] == "epa.mapa.mlflow_links.v1" &&
            links["report_sha256"] == sha && runs.is_a?(Array) &&
            runs.length == expected.length && expected.length == 9 &&
            runs.each_with_index.all? do |entry, index|
              entry.is_a?(Hash) &&
                [entry["protocol"], entry["model"]] == expected[index] &&
                entry["run_id"].is_a?(String) &&
                entry["run_id"].match?(/\A[0-9a-f]{32,64}\z/i)
            end && runs.map { |entry| entry["run_id"] }.uniq.length == 9
    raise Failure.new("mlflow_links_invalid") unless valid
    JSON.generate(links)
  rescue JSON::ParserError, KeyError
    raise Failure.new("mlflow_links_invalid")
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
