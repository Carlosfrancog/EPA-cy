class MapaRun < ApplicationRecord
  STATES = %w[queued running completed failed].freeze
  validates :seed, numericality: { only_integer: true, greater_than_or_equal_to: 0, less_than_or_equal_to: 999_999_999 }
  validates :status, inclusion: { in: STATES }

  def report
    JSON.parse(report_json) if status == "completed" && report_json.present?
  rescue JSON::ParserError
    nil
  end

  def extended_report
    return nil if extended_json.blank?
    JSON.parse(extended_json)
  rescue JSON::ParserError
    nil
  end

  def lupa_local_report
    return nil if lupa_local_json.blank?
    JSON.parse(lupa_local_json)
  rescue JSON::ParserError
    nil
  end

  def lupa_report
    return nil if lupa_json.blank?
    JSON.parse(lupa_json)
  rescue JSON::ParserError
    nil
  end

  def research_extended_report
    return nil if research_extended_json.blank?
    JSON.parse(research_extended_json)
  rescue JSON::ParserError
    nil
  end

  def research_report
    return nil if research_json.blank?
    JSON.parse(research_json)
  rescue JSON::ParserError
    nil
  end

  def mlflow_links
    return [] if mlflow_links_json.blank?
    JSON.parse(mlflow_links_json).fetch("runs", [])
  rescue JSON::ParserError, KeyError
    []
  end

  def waiting?
    %w[queued running].include?(status)
  end
end
