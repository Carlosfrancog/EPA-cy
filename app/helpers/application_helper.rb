module ApplicationHelper
  def section_icon(key)
    { "dashboard" => "◫", "datasets" => "◈", "experiments" => "◇", "mapa" => "✧", "models" => "◎",
      "integrity" => "⬡", "architecture" => "▦" }.fetch(key)
  end
end
