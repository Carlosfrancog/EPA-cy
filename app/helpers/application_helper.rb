module ApplicationHelper
  def section_icon(key)
    { "dashboard" => "◫", "datasets" => "◈", "experiments" => "◇", "models" => "◎",
      "integrity" => "⬡", "architecture" => "▦" }.fetch(key)
  end
end
