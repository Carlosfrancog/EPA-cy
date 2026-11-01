require "test_helper"
class LupaObservatoryControllerTest < ActionDispatch::IntegrationTest
  test "renders empty observer" do
    get lupa_observatory_path
    assert_response :success
    assert_select "h1", text: "Explicabilidade dos modelos"
  end

  test "invalid filters safely fall back" do
    get lupa_observatory_path, params: {protocol: "unknown", run_id: "evil"}
    assert_response :success
    assert_select "select[name=protocol] option[selected=selected][value=early]"
  end
end
