class AddResearchToMapaRuns < ActiveRecord::Migration[8.0]
  def change
    add_column :mapa_runs, :research_json, :text
    add_column :mapa_runs, :research_sha256, :string
  end
end
