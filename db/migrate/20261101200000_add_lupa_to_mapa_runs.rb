class AddLupaToMapaRuns < ActiveRecord::Migration[8.0]
  def change
    add_column :mapa_runs, :lupa_json, :text
    add_column :mapa_runs, :lupa_sha256, :string
  end
end
