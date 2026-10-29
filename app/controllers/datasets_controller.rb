class DatasetsController < ApplicationController
  def index
    @manifest_path = Rails.root.join("data", "demo", "manifest.json")
    @manifest = @manifest_path.file? ? JSON.parse(@manifest_path.read, max_nesting: 15) : nil
    @manifest = nil unless @manifest.is_a?(Hash) && @manifest["classification"] == "SYNTHETIC"
  rescue JSON::ParserError, ArgumentError
    @manifest = nil
  end
end
