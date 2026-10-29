class CreateExperimentRuns < ActiveRecord::Migration[8.0]
  def change
    create_table :experiment_runs do |t|
      t.string :model_key, null: false
      t.integer :seed, null: false
      t.string :status, null: false, default: "queued"
      t.text :report_json
      t.string :report_sha256
      t.string :input_sha256
      t.string :failure_code
      t.datetime :started_at
      t.datetime :finished_at
      t.timestamps
    end
    add_index :experiment_runs, [:created_at, :id]
    add_index :experiment_runs, :status
  end
end
