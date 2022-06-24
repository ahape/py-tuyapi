#!/usr/bin/python3
from tuya import Tuya



inst = Tuya("196.0.0.222", 6668, "asdf", "asdfasdfasdfasdf", "asdf")
inst.connect()
inst.get()
inst.set({ "set": "asdf" })
