class MapaRunTelemetry
  def self.duration_seconds(run)
    return nil unless run.started_at && run.finished_at
    seconds = run.finished_at - run.started_at
    seconds.finite? && seconds >= 0 ? seconds.round(2) : nil
  end

  def self.summarize(runs, now: Time.current)
    rows = runs.map do |run|
      { id: run.id, status: run.status, failure_code: run.failure_code,
        duration: duration_seconds(run),
        prolonged: run.status == "running" && run.started_at.present? &&
          (now - run.started_at) >= 900 }
    end
    durations = rows.filter_map { |row| row[:duration] if row[:status] == "completed" }
    { rows: rows,
      status_counts: MapaRun::STATES.to_h { |state| [state, rows.count { |row| row[:status] == state }] },
      prolonged_count: rows.count { |row| row[:prolonged] },
      mean_duration: durations.empty? ? nil : (durations.sum / durations.length).round(2) }
  end
end
