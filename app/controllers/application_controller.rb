class ApplicationController < ActionController::Base
  helper_method :active_section?

  private

  def active_section?(key)
    controller_name == key
  end
end
