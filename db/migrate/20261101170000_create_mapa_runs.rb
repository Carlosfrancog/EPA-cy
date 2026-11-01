class CreateMapaRuns < ActiveRecord::Migration[8.0]
  def change
    create_table :mapa_runs do |t|
      t.integer :seed, null: false
      t.string :status, null: false, default: "queued"
      t.text :report_json
      t.string :report_sha256
      t.string :dataset_manifest_sha256
      t.string :failure_code
      t.datetime :started_at
      t.datetime :finished_at
      t.timestamps
    end
    add_index :mapa_runs, :status
  end
end
