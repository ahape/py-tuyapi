#!/usr/bin/python3
import sys
import os
import json
from command_type import CommandType
from message import send_device_request

DEBUG = os.getenv("DEBUG") == "true"

if __name__ == "__main__":
  if DEBUG:
    from test_data import LIV_RM_3 as dev
    # Test GET
    send_device_request(dev, CommandType.DP_QUERY)

    # Test SET
    send_device_request(dev, CommandType.CONTROL)
  else:
    # TODO: Move all this to another module
    colors = [
      "000003e803e8", # red
      "00f003e80032", # blue
      "003c03e803e8", # yellow
    ]
    color_index = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 0

    with open("devices.json") as f:
      devs = json.load(f)

    for dev in devs:
      if dev["deviceType"] == "tuya":
        send_device_request(dev, CommandType.CONTROL)
