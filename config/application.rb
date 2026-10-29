require_relative "boot"
require "rails/all"

Bundler.require(*Rails.groups)

module EpaResearchPlatform
  class Application < Rails::Application
    config.load_defaults 8.0
    config.autoload_lib(ignore: %w[assets tasks])
    config.time_zone = "America/Sao_Paulo"
    config.active_record.schema_format = :ruby
    config.hosts.clear if Rails.env.development?
    config.generators.system_tests = nil
  end
end
