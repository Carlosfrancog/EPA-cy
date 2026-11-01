class AddResearchExtendedToMapaRuns < ActiveRecord::Migration[8.0]
  def change
    add_column :mapa_runs, :research_extended_json, :text
    add_column :mapa_runs, :research_extended_sha256, :string
  end
end
