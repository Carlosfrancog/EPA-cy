class MapaRun < ApplicationRecord
  STATES = %w[queued running completed failed].freeze
  validates :seed, numericality: { only_integer: true, greater_than_or_equal_to: 0, less_than_or_equal_to: 999_999_999 }
  validates :status, inclusion: { in: STATES }

  def report
    JSON.parse(report_json) if status == "completed" && report_json.present?
  rescue JSON::ParserError
    nil
  end

  def waiting?
    %w[queued running].include?(status)
  end
end
