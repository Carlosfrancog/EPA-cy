require "test_helper"

class SentinelResearchAuditTest < ActiveSupport::TestCase
  def create_run
    protocols = %w[early trajectory consolidated].each_with_index.map do |protocol, index|
      {protocol: protocol, cutoff_term: index + 1, fold_strategy: "GroupKFold_by_student",
       n_splits: 2, folds: [{fold: 1, model: "majority", train_students: 12, test_students: 8,
         class_support: {approved: 5, recovery: 2, failed: 1}}],
       temporal_holdout: {status: "not_identifiable", reason: "same_students_across_years"}}
    end
    MapaRun.create!(seed: 10, status: "completed", dataset_manifest_sha256: "a" * 64,
      research_json: {schema_version: "epa.mapa.research_protocol.v2",
        dataset_classification: "SYNTHETIC", source_manifest_sha256: "a" * 64,
        seed: 10, protocols: protocols}.to_json)
  end

  test "reports lack of independent temporal cohort without flagging structural corruption" do
    result = SentinelResearchAudit.inspect_run(create_run)
    assert_equal "checked", result.first[:status]
    assert result.first[:findings].any? { |message| message.include?("não identificável") }
    assert_equal "absent", result.last[:status]
  end

  test "flags unsupported split declaration" do
    run = create_run
    data = run.research_report
    data["protocols"][0]["fold_strategy"] = "random_rows"
    run.update!(research_json: data.to_json)
    assert_equal "warning", SentinelResearchAudit.inspect_run(run).first[:status]
  end

  test "rejects altered dataset provenance" do
    run = create_run
    run.update!(dataset_manifest_sha256: "b" * 64)
    assert_equal "invalid", SentinelResearchAudit.inspect_run(run).first[:status]
  end
end
