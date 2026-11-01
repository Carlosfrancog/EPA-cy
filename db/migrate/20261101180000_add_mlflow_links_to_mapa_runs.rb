class AddMlflowLinksToMapaRuns < ActiveRecord::Migration[8.0]
  def change
    add_column :mapa_runs, :mlflow_links_json, :text
  end
end
