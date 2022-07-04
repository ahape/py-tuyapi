#!/usr/bin/python3
import sys
import os
import json
import time
from threading import Thread, Lock
from command_type import CommandType
from message import send_device_request
from settings import Settings

DEBUG = os.getenv("DEBUG") == "true"

active_threads = 0
active_threads_lock = Lock()

def thread_function(dev, color):
  global active_threads

  # TODO: Figure out smarter way to update threadsafe data
  with active_threads_lock:
    active_threads += 1

  turn_color_if_on(dev, color)

  with active_threads_lock:
    active_threads -= 1

def turn_color_if_on(dev, color):
  resp = send_device_request(dev, CommandType.DP_QUERY)[0] # Expect only one response for now
  settings = Settings.load(resp["data"]["dps"])

  if settings.on:
    send_device_request(dev, CommandType.CONTROL, Settings(on=True, color=color))

def run():
  color = sys.argv[1] if len(sys.argv) > 1 else None

  trace_start = time.time()

  with open("devices.json") as f:
    devs = json.load(f)

  for dev in devs:
    if dev["deviceType"] == "tuya":
      Thread(target=thread_function, args=(dev,color)).start() # multi-threaded
      #turn_color_if_on(dev,color) # single threaded

  while True:
    with active_threads_lock:
      if active_threads == 0: break

  print(f"Total time: {time.time() - trace_start:n} seconds")

def test():
  from test_data import LIV_RM_3 as dev
  # Test GET
  send_device_request(dev, CommandType.DP_QUERY)

  # Test SET
  send_device_request(dev, CommandType.CONTROL)

if __name__ == "__main__":
  if DEBUG: test()
  else: run()
