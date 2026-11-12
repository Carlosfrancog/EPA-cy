class CreateNativeMapaRuns < ActiveRecord::Migration[8.0]
  def change
    create_table :native_mapa_runs do |t|
      t.integer :seed, null: false
      t.integer :max_students, null: false
      t.string :dataset_key, null: false
      t.text :model_keys_json, null: false
      t.string :status, null: false, default: "queued"
      t.text :report_json
      t.string :report_sha256
      t.string :failure_code
      t.datetime :started_at
      t.datetime :finished_at
      t.timestamps
    end
    add_index :native_mapa_runs, :status
  end
end
