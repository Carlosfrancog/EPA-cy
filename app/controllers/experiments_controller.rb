class ExperimentsController < ApplicationController
  OPTIONS = {
    "majority" => "Majority baseline",
    "logistic_regression" => "Regressão logística",
    "random_forest" => "Random Forest"
  }.freeze

  def index
    @options = OPTIONS
    @experiment = nil
  end

  def preview
    @options = OPTIONS
    selected = params.fetch(:model, "").to_s
    seed_string = params.fetch(:seed, "").to_s
    unless OPTIONS.key?(selected) && seed_string.match?(/\A\d{1,9}\z/)
      flash.now[:alert] = "Selecione um modelo e uma seed inteira positiva de até 9 dígitos."
      @experiment = nil
      return render :index, status: :unprocessable_entity
    end
    @experiment = { model: selected, model_label: OPTIONS.fetch(selected), seed: seed_string.to_i,
                    dataset: "data/demo/academic_history.parquet",
                    status: "CONFIGURADO — NÃO EXECUTADO" }
    render :index
  end
end
