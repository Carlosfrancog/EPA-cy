class MapaEvaluationsController < ApplicationController
  def index
    @protocol = MapaEvaluation::PROTOCOLS.include?(params[:protocol]) ? params[:protocol] : "early"
    @metric = MapaEvaluation::METRICS.include?(params[:metric]) ? params[:metric] : "f1_macro"
    @model = (["all"] + MapaEvaluation::MODELS).include?(params[:model]) ? params[:model] : "all"
    @evaluation = MapaEvaluation.build(MapaRun.where(status: "completed").order(created_at: :desc).limit(200),
                                       protocol: @protocol, metric: @metric, model: @model)
  end
end
