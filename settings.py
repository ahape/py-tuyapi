class Settings():
  def __init__(self, on=None, color=None):
    self.on = on
    self.color = color

  def load(json):
    settings = Settings()
    settings.on = bool(json["20"])
    settings.color = from_tuya_color(json["24"]) if "24" in json else None
    return settings

  def serialize(self):
    ret = {}
    if self.on != None:
      ret["20"] = self.on
    if self.color != None:
      ret["21"] = "colour"
      ret["24"] = to_tuya_color(self.color)
    return ret

def to_tuya_color(color):
  if color == "red":
    return "000003e803e8"
  if color == "blue":
    return "00f003e80032"
  if color == "yellow":
    return "003c03e803e8"
  return "003c03e803e8"

def from_tuya_color(color):
  if color == "000003e803e8":
    return "red"
  if color == "00f003e80032":
    return "blue"
  if color == "003c03e803e8":
    return "yellow"

  print(f"WARN: Couldn't parse color {color}")
  return None
