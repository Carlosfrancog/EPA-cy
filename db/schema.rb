ActiveRecord::Schema[8.0].define(version: 2026_11_01_220000) do
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
  create_table "mapa_runs", force: :cascade do |t|
    t.integer "seed", null: false
    t.string "status", default: "queued", null: false
    t.text "report_json"
    t.string "report_sha256"
    t.string "dataset_manifest_sha256"
    t.text "mlflow_links_json"
    t.text "research_json"
    t.string "research_sha256"
    t.text "lupa_json"
    t.string "lupa_sha256"
    t.text "lupa_local_json"
    t.string "lupa_local_sha256"
    t.text "extended_json"
    t.string "extended_sha256"
    t.string "failure_code"
    t.datetime "started_at"
    t.datetime "finished_at"
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["status"], name: "index_mapa_runs_on_status"
  end
end
