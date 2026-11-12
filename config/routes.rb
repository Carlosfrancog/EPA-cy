Rails.application.routes.draw do
  root "dashboard#index"
  get "/datasets", to: "datasets#index", as: :datasets
  resources :experiments, only: [:index, :show, :create]
  post "/experiments/preview", to: "experiments#preview", as: :preview_experiment
  get "/lupa", to: "lupa_observatory#index", as: :lupa_observatory
  get "/mapa/evaluation", to: "mapa_evaluations#index", as: :mapa_evaluation
  resources :native_mapa_runs, only: [:index, :show, :create], path: "mapa/native"
  resources :mapa_runs, only: [:index, :show, :create], path: "mapa"
  get "/models", to: "models#index", as: :models
  get "/integrity", to: "integrity#index", as: :integrity
  get "/architecture", to: "architecture#index", as: :architecture
  get "/up", to: ->(_env) { [200, {"Content-Type" => "text/plain"}, ["OK"]] }, as: :health
end
