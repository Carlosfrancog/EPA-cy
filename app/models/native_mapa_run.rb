class NativeMapaRun < ApplicationRecord
  STATES = %w[queued running completed failed].freeze
  ALGORITHMS = %w[majority logistic_regression random_forest mlp].freeze
  validates :seed, numericality: { only_integer: true, in: 0..999_999_999 }
  validates :max_students, numericality: { only_integer: true, in: 8..5_000 }
  validates :dataset_key, format: { with: /\Amapa-features-[a-zA-Z0-9_-]+\z/ }
  validates :status, inclusion: { in: STATES }
  validate :valid_models

  def models
    JSON.parse(model_keys_json)
  rescue JSON::ParserError, TypeError
    []
  end

  def report
    JSON.parse(report_json) if status == "completed" && report_json.present?
  rescue JSON::ParserError
    nil
  end

  def waiting?
    %w[queued running].include?(status)
  end

  private

  def valid_models
    errors.add(:model_keys_json, "invalid algorithms") unless
      models.any? && models.uniq == models && (models - ALGORITHMS).empty?
  end
end
