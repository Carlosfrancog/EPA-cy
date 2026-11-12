class NativeMapaRunsController < ApplicationController
  before_action :require_local!, only: :create

  def index
    @datasets = NativeMapaRunner.datasets
    @runs = NativeMapaRun.order(created_at: :desc).limit(30)
  end

  def create
    dataset_key = params.fetch(:dataset_key, "").to_s
    seed_text = params.fetch(:seed, "").to_s
    students_text = params.fetch(:max_students, "").to_s
    models = Array(params[:models]).map(&:to_s)
    valid = NativeMapaRunner.datasets.include?(dataset_key) &&
            seed_text.match?(/\A\d{1,9}\z/) &&
            students_text.match?(/\A\d{1,4}\z/) &&
            models.any? && models.uniq == models &&
            (models - NativeMapaRun::ALGORITHMS).empty?
    unless valid
      return redirect_to native_mapa_runs_path, alert: "Parâmetros inválidos ou dataset indisponível.", status: :see_other
    end
    run = NativeMapaRun.new(dataset_key: dataset_key, seed: seed_text.to_i,
                            max_students: students_text.to_i, model_keys_json: JSON.generate(models))
    unless run.save
      return redirect_to native_mapa_runs_path, alert: "Verifique limites (8–5000 estudantes).", status: :see_other
    end
    NativeMapaRunnerJob.perform_later(run.id)
    redirect_to native_mapa_run_path(run), notice: "Treinamento nativo enfileirado.", status: :see_other
  end

  def show
    @run = NativeMapaRun.find(params[:id])
    @report = @run.report
  end

  private

  def require_local!
    return if (Rails.env.development? || Rails.env.test?) && request.local?
    head :forbidden
  end
end
