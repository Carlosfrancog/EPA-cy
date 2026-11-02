require "test_helper"
class HomologationRoutesTest < ActionDispatch::IntegrationTest
  test "research pages respond without needing active jobs" do
    [mapa_runs_path, mapa_evaluation_path, lupa_observatory_path, integrity_path].each do |path|
      get path
      assert_response :success
    end
  end
end
