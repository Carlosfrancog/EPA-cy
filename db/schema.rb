# Generated from the initial laboratory migration.
ActiveRecord::Schema[8.0].define(version: 2026_10_29_210000) do
  create_table "experiment_runs", force: :cascade do |t|
    t.string "model_key", null: false
    t.integer "seed", null: false
    t.string "status", default: "queued", null: false
    t.text "report_json"
    t.string "report_sha256"
    t.string "input_sha256"
    t.string "failure_code"
    t.datetime "started_at"
    t.datetime "finished_at"
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["created_at", "id"], name: "index_experiment_runs_on_created_at_and_id"
    t.index ["status"], name: "index_experiment_runs_on_status"
  end
end
