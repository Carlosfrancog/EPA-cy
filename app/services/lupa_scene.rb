# Three-dimensional visualization payload built only from verified LUPA reports.
class LupaScene
  def self.for_run(run)
    return nil unless run&.status == "completed"
    protocols = LupaObservatory::PROTOCOLS.map do |protocol|
      entry = LupaObservatory.compare([run], protocol: protocol)[:rows].first
      return nil unless entry
      { protocol: protocol, score: entry[:score], test_observations: entry[:test_observations],
        features: entry[:features].map do |feature|
          { name: feature["name"], importance: feature["mean_f1_drop"],
            dispersion: feature["std_f1_drop"] }
        end }
    end
    return nil unless protocols.map { |p| p[:features].map { |f| f[:name] }.sort }.uniq.size == 1
    { schema: "epa.lupa.scene.v1", run_id: run.id,
      manifest_sha256: run.dataset_manifest_sha256,
      axis: { x: "feature_index", y: "signed_macro_f1_drop", z: "prediction_cutoff" },
      protocols: protocols }
  end
end
