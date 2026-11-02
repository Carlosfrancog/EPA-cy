require "digest"
require "json"

# Read-only integrity audit of persisted MAPA research artifacts.
# LEDGER: provenance/digest checks. SENTINEL: declared schema/split checks.
class MapaIntegrityAudit
  ARTIFACTS = {
    "MAPA" => [:report_json, :report_sha256, "epa.mapa.benchmark.v1"],
    "MAPA Research" => [:research_json, :research_sha256, "epa.mapa.research_protocol.v2"],
    "MAPA Extended" => [:extended_json, :extended_sha256, "epa.mapa.extended_models.v1"],
    "Extended Research" => [:research_extended_json, :research_extended_sha256, "epa.mapa.research_extended.v1"],
    "LUPA" => [:lupa_json, :lupa_sha256, "epa.lupa.explainability.v1"],
    "LUPA Local" => [:lupa_local_json, :lupa_local_sha256, "epa.lupa.local_diagnostics.v1"]
  }.freeze

  def self.inspect_run(run)
    checked = ARTIFACTS.map do |name, (raw_attribute, hash_attribute, schema)|
      raw = run.public_send(raw_attribute)
      expected = run.public_send(hash_attribute)
      if raw.blank? && expected.blank?
        { name: name, status: "absent", reasons: ["Artefato não disponível nesta execução."] }
      elsif !raw.is_a?(String) || !expected.is_a?(String) || !expected.match?(/\A[0-9a-f]{64}\z/i)
        { name: name, status: "invalid", reasons: ["Conteúdo ou digest SHA-256 ausente/inválido."] }
      else
        actual = Digest::SHA256.hexdigest(raw)
        if actual != expected.downcase
          { name: name, status: "invalid", reasons: ["Digest não corresponde ao conteúdo armazenado."] }
        else
          begin
            data = JSON.parse(raw)
            report_hash = data["dataset_manifest_sha256"] || data["source_manifest_sha256"]
            matches = data["schema_version"] == schema &&
              data["dataset_classification"] == "SYNTHETIC" &&
              report_hash == run.dataset_manifest_sha256 &&
              (data["seed"].nil? || data["seed"] == run.seed) &&
              (data["protocols"].nil? || (data["protocols"].is_a?(Array) &&
                data["protocols"].map { |p| p["cutoff_term"] } == [1, 2, 3]))
            { name: name, status: matches ? "verified" : "invalid",
              reasons: matches ? [] : ["Schema, classificação, seed ou manifesto divergentes."] }
          rescue JSON::ParserError, TypeError
            { name: name, status: "invalid", reasons: ["JSON não analisável."] }
          end
        end
      end
    end
    { run_id: run.id, run_status: run.status, artifacts: checked,
      verified: checked.count { |a| a[:status] == "verified" },
      invalid: checked.count { |a| a[:status] == "invalid" },
      absent: checked.count { |a| a[:status] == "absent" },
      warning: "Integridade local dos bytes não comprova autenticidade de origem, assinatura externa, ausência de leakage ou validade empírica." }
  end
end
