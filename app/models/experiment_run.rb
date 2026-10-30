class ExperimentRun < ApplicationRecord
  MODELS = {
    "majority" => "Majority baseline",
    "logistic_regression" => "Regressão logística",
    "random_forest" => "Random Forest"
  }.freeze
  STATES = %w[queued running completed failed quarantined].freeze

  validates :model_key, inclusion: { in: MODELS.keys }
  validates :seed, numericality: { only_integer: true, greater_than_or_equal_to: 0, less_than_or_equal_to: 999_999_999 }
  validates :status, inclusion: { in: STATES }

  def model_label
    MODELS.fetch(model_key)
  end

  def report
    return nil unless completed? && report_json.present?
    JSON.parse(report_json)
  rescue JSON::ParserError
    nil
  end

  def completed?
    status == "completed"
  end

  def waiting?
    %w[queued running].include?(status)
  end
end
