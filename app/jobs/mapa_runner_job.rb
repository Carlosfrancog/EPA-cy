class MapaRunnerJob < ApplicationJob
  queue_as :default

  def perform(run_id)
    claimed = MapaRun.where(id: run_id, status: "queued")
                     .update_all(status: "running", started_at: Time.current, updated_at: Time.current)
    return unless claimed == 1

    run = MapaRun.find(run_id)
    begin
      evidence = runner.call(run)
      run.update!(status: "completed", report_json: evidence.fetch(:json),
                  report_sha256: evidence.fetch(:sha256),
                  dataset_manifest_sha256: evidence.fetch(:dataset_sha256),
                  mlflow_links_json: evidence[:mlflow_links_json],
                  lupa_local_json: evidence[:lupa_local_json], lupa_local_sha256: evidence[:lupa_local_sha256],
                  lupa_json: evidence[:lupa_json], lupa_sha256: evidence[:lupa_sha256],
                  research_json: evidence[:research_json], research_sha256: evidence[:research_sha256],
                  finished_at: Time.current)
    rescue MapaPythonRunner::Failure => e
      run.update!(status: "failed", failure_code: e.code, finished_at: Time.current)
    rescue StandardError => e
      Rails.logger.error("MAPA run #{run_id} failed: #{e.class}")
      run.update!(status: "failed", failure_code: "internal_error", finished_at: Time.current)
    end
  end

  private

  def runner
    MapaPythonRunner.new
  end
end
