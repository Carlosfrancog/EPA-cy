require "json"
require "digest"
require "open3"
require "timeout"
require "pathname"
require "fileutils"

class NativeMapaRunner
  class Failure < StandardError
    attr_reader :code
    def initialize(code)
      @code = code
      super(code)
    end
  end

  TIMEOUT_SECONDS = 900
  MAX_REPORT_BYTES = 350_000

  def initialize(root: Rails.root, python: ENV.fetch("EPA_PYTHON_EXECUTABLE", "python3"))
    @root = Pathname.new(root).realpath
    @python = python
  end

  def self.datasets(root = Rails.root)
    base = Pathname.new(root).join("data")
    return [] unless base.directory?
    base.children.select(&:directory?).filter_map do |path|
      next unless path.basename.to_s.match?(/\Amapa-features-[a-zA-Z0-9_-]+\z/)
      manifest = path.join("manifest.json")
      next unless manifest.file? && !path.symlink?
      begin
        info = JSON.parse(manifest.read)
        path.basename.to_s if info["schema_version"] == "epa.mapa.feature_dataset.v1" &&
                              info["classification"] == "SYNTHETIC"
      rescue JSON::ParserError, Errno::EACCES
        nil
      end
    end.sort
  end

  def call(run)
    raise Failure.new("dataset_not_allowed") unless self.class.datasets(@root).include?(run.dataset_key)
    dataset = @root.join("data", run.dataset_key)
    raise Failure.new("unsafe_dataset_path") unless dataset.realpath.to_s.start_with?(@root.join("data").realpath.to_s + File::SEPARATOR)
    target = @root.join("data", "native-mapa-runs", run.id.to_s)
    FileUtils.mkdir_p(target)
    output = target.join("report.json")
    raise Failure.new("output_exists") if output.exist?

    args = ["-m", "epa.core_engine.mapa_native_training",
            "--features", dataset.to_s, "--max-students", run.max_students.to_s,
            "--seed", run.seed.to_s, "--models", *run.models, "--output", output.to_s]
    _stdout, _stderr, status = Timeout.timeout(TIMEOUT_SECONDS) do
      Open3.capture3({ "PYTHONPATH" => @root.to_s }, @python, *args, chdir: @root.to_s)
    end
    raise Failure.new("engine_failed") unless status.success?
    raise Failure.new("report_missing") unless output.file?
    raise Failure.new("report_too_large") if output.size > MAX_REPORT_BYTES
    raw = output.binread
    report = JSON.parse(raw)
    valid = report["schema_version"] == "epa.mapa.native_training.v1" &&
            report["research_status"] == "SYNTHETIC_NOT_EMPIRICALLY_VALIDATED" &&
            report["seed"] == run.seed &&
            report["selected_students"].is_a?(Integer) &&
            report["selected_students"].between?(8, run.max_students) &&
            report["feature_manifest_sha256"] == Digest::SHA256.file(dataset.join("manifest.json")).hexdigest &&
            report["protocols"].is_a?(Array) &&
            report["protocols"].map { |p| p["cutoff_term"] } == [1, 2, 3] &&
            report["protocols"].all? { |p| p["results"].map { |r| r["model"] } == run.models }
    raise Failure.new("invalid_report") unless valid
    { json: raw, sha256: Digest::SHA256.hexdigest(raw) }
  rescue Timeout::Error
    raise Failure.new("engine_timeout")
  rescue Errno::ENOENT
    raise Failure.new("python_missing")
  rescue JSON::ParserError, KeyError, NoMethodError
    raise Failure.new("invalid_report")
  end
end
