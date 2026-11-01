class LupaObservatoryController < ApplicationController
  def index
    @protocol = LupaObservatory::PROTOCOLS.include?(params[:protocol]) ? params[:protocol] : "early"
    @selected_run = params[:run_id].to_s.match?(/\A\d{1,12}\z/) ? params[:run_id].to_i : nil
    @observatory = LupaObservatory.compare(
      MapaRun.where(status: "completed").order(id: :desc).limit(100),
      protocol: @protocol
    )
    @row = @observatory[:rows].find { |r| r[:run_id] == @selected_run } || @observatory[:rows].first
  end
end
