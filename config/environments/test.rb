Rails.application.configure do
  config.enable_reloading = false
  config.eager_load = ENV["CI"].present?
  config.consider_all_requests_local = true
  config.action_controller.perform_caching = false
  # Integration tests post without CSRF tokens; never disable this in production.
  config.action_controller.allow_forgery_protection = false
  config.action_dispatch.show_exceptions = :rescuable
end
