class ExperimentsController < ApplicationController
  before_action :require_local_execution!, only: :create

  def index
    @options = ExperimentRun::MODELS
    @experiment = nil
    @runs = ExperimentRun.order(created_at: :desc).limit(30)
  end

  def preview
    @options = ExperimentRun::MODELS
    @runs = ExperimentRun.order(created_at: :desc).limit(30)
    selected = params.fetch(:model, "").to_s
    seed_string = params.fetch(:seed, "").to_s
    unless valid_request?(selected, seed_string)
      flash.now[:alert] = "Selecione um modelo válido e uma seed inteira de até 9 dígitos."
      @experiment = nil
      return render :index, status: :unprocessable_entity
    end
    @experiment = { model: selected, model_label: @options.fetch(selected), seed: seed_string.to_i,
                    dataset: "data/demo/academic_history.parquet",
                    status: "CONFIGURADO — NÃO EXECUTADO" }
    render :index
  end

  def create
    selected = params.fetch(:model, "").to_s
    seed_string = params.fetch(:seed, "").to_s
    unless valid_request?(selected, seed_string)
      redirect_to experiments_path, alert: "Parâmetros inválidos.", status: :see_other
      return
    end

    run = ExperimentRun.create!(model_key: selected, seed: seed_string.to_i, status: "queued")
    ExperimentRunnerJob.perform_later(run.id)
    redirect_to experiment_path(run), notice: "Experimento enfileirado.", status: :see_other
  end

  def show
    @run = ExperimentRun.find(params[:id])
    @report = @run.report
    @selected_result = @report&.fetch("results", [])&.find { |r| r["model"] == @run.model_key }
  end

  private

  def valid_request?(model, seed)
    ExperimentRun::MODELS.key?(model) && seed.match?(/\A\d{1,9}\z/)
  end

  def require_local_execution!
    return if (Rails.env.development? || Rails.env.test?) && request.local?
    head :forbidden
  end
end
