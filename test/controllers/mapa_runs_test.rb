require "test_helper"

class MapaRunsTest < ActionDispatch::IntegrationTest
  include ActiveJob::TestHelper

  test "MAPA index and form are navigable" do
    get mapa_runs_path
    assert_response :success
    assert_select "h1", text: "Treinamento MAPA"
    assert_select "form[action='#{mapa_runs_path}']"
  end

  test "MAPA experiment queues worker" do
    assert_difference("MapaRun.count", 1) do
      assert_enqueued_with(job: MapaRunnerJob) do
        post mapa_runs_path, params: { seed: "42" }
      end
    end
    assert_response :see_other
    assert_redirected_to mapa_run_path(MapaRun.order(:id).last)
  end

  test "MAPA does not accept invalid seed" do
    assert_no_difference("MapaRun.count") { post mapa_runs_path, params: { seed: "abc" } }
    assert_redirected_to mapa_runs_path
  end

  test "MAPA report renders three class counts without invented scores" do
    run = MapaRun.create!(seed: 42, status: "completed", report_json: {
      baselines: [{
        cutoff_term: 1, protocol: "early", classes: %w[approved recovery failed],
        train_observations: 30, test_observations: 10,
        test_class_counts: { approved: 6, recovery: 3, failed: 1 },
        results: [{ model: "majority", accuracy: 0.6, balanced_accuracy: 0.333,
                    f1_macro: 0.25, recall_by_class: { approved: 1.0, recovery: 0.0, failed: 0.0 },
                    confusion_matrix: [[6, 0, 0], [3, 0, 0], [1, 0, 0]] }]
      }]
    }.to_json)
    get mapa_run_path(run)
    assert_response :success
    assert_select "body", /MAPA Early/
    assert_select "body", /Recupera|recovery/
  end
end
