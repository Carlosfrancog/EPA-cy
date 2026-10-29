Rails.application.routes.draw do
  root "dashboard#index"
  get "/datasets", to: "datasets#index", as: :datasets
  resources :experiments, only: [:index, :show, :create]
  post "/experiments/preview", to: "experiments#preview", as: :preview_experiment
  get "/models", to: "models#index", as: :models
  get "/integrity", to: "integrity#index", as: :integrity
  get "/architecture", to: "architecture#index", as: :architecture
  get "/up", to: ->(_env) { [200, {"Content-Type" => "text/plain"}, ["OK"]] }, as: :health
end
