require "test_helper"

class NavigationTest < ActionDispatch::IntegrationTest
  test "all workspace pages respond" do
    ["/", "/datasets", "/experiments", "/models", "/integrity", "/architecture"].each do |path|
      get path
      assert_response :success
    end
  end

  test "experiment preview never executes a job" do
    post "/experiments/preview", params: { model: "random_forest", seed: "42" }
    assert_response :success
    assert_select "body", /CONFIGURAÇÃO|Configuração|Configurar/
    assert_select "body", /Não executado/
  end

  test "experiment rejects unrecognized model" do
    post "/experiments/preview", params: { model: "unsafe_model", seed: "42" }
    assert_response :unprocessable_entity
  end
end
