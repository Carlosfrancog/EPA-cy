class NativeMapaRunnerJob < ApplicationJob
  queue_as :default

  def perform(run_id)
    claimed = NativeMapaRun.where(id: run_id, status: "queued")
                           .update_all(status: "running", started_at: Time.current, updated_at: Time.current)
    return unless claimed == 1
    run = NativeMapaRun.find(run_id)
    begin
      evidence = NativeMapaRunner.new.call(run)
      run.update!(status: "completed", report_json: evidence.fetch(:json),
                  report_sha256: evidence.fetch(:sha256), finished_at: Time.current)
    rescue NativeMapaRunner::Failure => error
      run.update!(status: "failed", failure_code: error.code, finished_at: Time.current)
    rescue StandardError => error
      Rails.logger.error("Native MAPA run #{run_id}: #{error.class}")
      run.update!(status: "failed", failure_code: "internal_error", finished_at: Time.current)
    end
  end
end
