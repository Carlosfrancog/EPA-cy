require "test_helper"
class LupaSceneExplorationTest < ActionDispatch::IntegrationTest
  test "without complete reports no interactive filters render" do
    get lupa_observatory_path
    assert_response :success
    assert_select "[data-feature-filter]", count: 0
  end
end
