#!/usr/bin/python3
import sys
import os
import json
from command_type import CommandType
from message import send_device_request
from settings import Settings

DEBUG = os.getenv("DEBUG") == "true"

if __name__ == "__main__":
  if DEBUG:
    from test_data import LIV_RM_3 as dev
    # Test GET
    send_device_request(dev, CommandType.DP_QUERY, Settings())

    # Test SET
    send_device_request(dev, CommandType.CONTROL, Settings())
  else:
    with open("devices.json") as f:
      devs = json.load(f)

    for dev in devs:
      if dev["deviceType"] == "tuya" and dev["name"] == "LivRm3": # testing
        send_device_request(dev, CommandType.CONTROL, Settings(on=True, color="red"))
