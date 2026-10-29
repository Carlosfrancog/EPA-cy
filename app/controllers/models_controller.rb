class ModelsController < ApplicationController
  def index
    @models = [
      { name: "Majority baseline", key: "majority", role: "Comparação mínima", state: "Código disponível" },
      { name: "Regressão logística", key: "logistic_regression", role: "Baseline linear", state: "Código disponível" },
      { name: "Random Forest", key: "random_forest", role: "Classificação não linear", state: "Código disponível" }
    ]
  end
end
