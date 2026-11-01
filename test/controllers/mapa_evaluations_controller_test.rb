require "test_helper"

class MapaEvaluationsControllerTest < ActionDispatch::IntegrationTest
  test "evaluation page loads with no experiments" do
    get mapa_evaluation_path
    assert_response :success
    assert_select "h1", text: "Comparação científica de experimentos"
  end

  test "unrecognized filters default safely" do
    get mapa_evaluation_path, params: {protocol: "malicious", metric: "bad", model: "xyz"}
    assert_response :success
    assert_select "select[name=protocol] option[selected=selected][value=early]"
  end
end
