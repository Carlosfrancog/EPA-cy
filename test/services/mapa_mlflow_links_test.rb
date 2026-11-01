require "test_helper"

class MapaMlflowLinksTest < ActiveSupport::TestCase
  test "valid nine unique MLflow links are bound to report digest" do
    runner = MapaPythonRunner.new
    report = { "baselines" => %w[early trajectory consolidated].map do |protocol|
      { "protocol" => protocol, "results" => %w[majority logistic_regression random_forest].map { |m| { "model" => m } } }
    end }
    links = {
      "schema_version" => "epa.mapa.mlflow_links.v1", "report_sha256" => "a" * 64,
      "runs" => report["baselines"].flat_map.with_index do |block, i|
        block["results"].each_with_index.map { |result, j| { "protocol" => block["protocol"],
                                                            "model" => result["model"],
                                                            "run_id" => (i * 3 + j + 1).to_s(16).rjust(32, "0") } }
      end
    }
    require "tmpdir"
    Dir.mktmpdir do |dir|
      path = Pathname(dir).join("links.json")
      path.write(JSON.generate(links))
      assert_equal 9, JSON.parse(runner.send(:verified_links!, path, report, "a" * 64))["runs"].length
      assert_raises(MapaPythonRunner::Failure) { runner.send(:verified_links!, path, report, "b" * 64) }
      links["runs"][0]["run_id"] = links["runs"][1]["run_id"]
      path.write(JSON.generate(links))
      assert_raises(MapaPythonRunner::Failure) { runner.send(:verified_links!, path, report, "a" * 64) }
    end
  end
end
