Rails.application.configure do
  config.enable_reloading = false
  config.eager_load = true
  config.consider_all_requests_local = false
  config.log_level = :info
  config.force_ssl = ENV["EPA_FORCE_SSL"] == "1"
  config.assets.compile = false
  config.public_file_server.enabled = ENV["RAILS_SERVE_STATIC_FILES"].present?
  # No background execution in production until authentication and a durable queue exist.
  config.active_job.queue_adapter = :async
end
