class MapaRunsController < ApplicationController
  before_action :require_local_execution!, only: :create

  def index
    @runs = MapaRun.order(created_at: :desc).limit(30)
    @telemetry = MapaRunTelemetry.summarize(@runs)
  end

  def create
    seed = params.fetch(:seed, "").to_s
    unless seed.match?(/\A\d{1,9}\z/)
      return redirect_to mapa_runs_path, alert: "Seed inválida.", status: :see_other
    end

    run = MapaRun.create!(seed: seed.to_i)
    MapaRunnerJob.perform_later(run.id)
    redirect_to mapa_run_path(run), notice: "Treinamento MAPA enfileirado.", status: :see_other
  end

  def show
    @run = MapaRun.find(params[:id])
    @report = @run.report
  end

  private

  def require_local_execution!
    return if (Rails.env.development? || Rails.env.test?) && request.local?
    head :forbidden
  end
end
