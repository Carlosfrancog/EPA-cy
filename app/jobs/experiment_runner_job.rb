class ExperimentRunnerJob < ApplicationJob
  queue_as :default

  def perform(run_id)
    # Atomic claim: duplicate deliveries do not run the same experiment twice.
    claimed = ExperimentRun.where(id: run_id, status: "queued")
                           .update_all(status: "running", started_at: Time.current, updated_at: Time.current)
    return unless claimed == 1

    run = ExperimentRun.find(run_id)
    begin
      evidence = runner.call(run)
      run.update!(status: "completed", report_json: evidence.fetch(:json),
                  report_sha256: evidence.fetch(:sha256), input_sha256: evidence.fetch(:input_sha256),
                  finished_at: Time.current)
    rescue EpaPythonRunner::Failure => e
      run.update!(status: "failed", failure_code: e.code, finished_at: Time.current)
    rescue StandardError => e
      Rails.logger.error("EPA experiment run #{run_id} failed: #{e.class}")
      run.update!(status: "failed", failure_code: "internal_error", finished_at: Time.current)
    end
  end

  private

  def runner
    EpaPythonRunner.new
  end
end
