class MapaEvaluationsController < ApplicationController
  def index
    @protocol = MapaEvaluation::PROTOCOLS.include?(params[:protocol]) ? params[:protocol] : "early"
    @metric = MapaEvaluation::METRICS.include?(params[:metric]) ? params[:metric] : "f1_macro"
    @model = (["all"] + MapaEvaluation::MODELS).include?(params[:model]) ? params[:model] : "all"
    @evaluation = MapaEvaluation.build(MapaRun.where(status: "completed").order(created_at: :desc).limit(200),
                                       protocol: @protocol, metric: @metric, model: @model)
    @evidence = @evaluation[:best_per_model].to_h do |row|
      run = MapaRun.find_by(id: row[:run_id])
      [[row[:run_id], row[:model]], run && MapaEvidenceGates::MODELS.include?(row[:model]) ? MapaEvidenceGates.assess(run, protocol: @protocol, model: row[:model]) : {status: "insufficient_evidence", reasons: ["Modelo estendido sem validação cruzada própria."], deployable: false}]
    end
  end
end
