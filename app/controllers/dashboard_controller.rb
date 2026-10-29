class DashboardController < ApplicationController
  def index
    @dataset = demo_dataset
  end

  private

  def demo_dataset
    path = Rails.root.join("data", "demo", "manifest.json")
    return nil unless path.file?

    data = JSON.parse(path.read, max_nesting: 15)
    return nil unless data["schema_version"] == "epa.genesis.dataset.v1" && data["classification"] == "SYNTHETIC"

    data
  rescue JSON::ParserError, ArgumentError
    nil
  end
end
