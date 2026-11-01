class AddLupaLocalToMapaRuns < ActiveRecord::Migration[8.0]
  def change
    add_column :mapa_runs, :lupa_local_json, :text
    add_column :mapa_runs, :lupa_local_sha256, :string
  end
end
