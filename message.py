#!/usr/bin/python3
from datetime import datetime
import time
import socket
import json
from Crypto.Cipher import AES
import base64
import hashlib

KEY = str(hashlib.md5(b"yGAdlopoPVldABfn")).encode("utf8")

"""
xap7CuPc/SAeOjdjlCk8Xo3T5ouakCTpCBUOKVDVHPCz6T5l4QzOgnOwZylKwSy3tda3kfU0JGVv8ATwCRKOUMnzevuhNVb6bj55MJKgQy1Ss/5Io9yPW1kxWcvAa6LJ+bfjNNWAmvLtJTOdEsovwyHtP0Bgf91Rr+Pq+dEMMcw=

bytearray([0x6c ,0x1e, 0xc8, 0xe2, 0xbb, 0x9b ,0xb5, 0x9a, 0xb5, 0x0b, 0x0d, 0xaf, 0x64, 0x9b, 0x41, 0x0a])


base64:
  bB7I4rubtZq1Cw2vZJtBCg==
"""

def create_socket():
  with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    # LivRm3
    s.connect(("192.168.1.137", 6668))

    msg = encode({
      "gwId": "ebe0828eedb64aacc0wxvf",
      "devId": "ebe0828eedb64aacc0wxvf",
      "t": str(int(time.time())),
      "dps": {},
      "uid": "ebe0828eedb64aacc0wxvf"
    })

    s.sendall(msg)

    data = s.recv(1024)

    print(f"Received {data!r}")

def encode(json_dict):
  data = json.dumps(json_dict).replace(" ", "")
  while len(data) % 16 != 0:
    data += " "

  enc = base64.b64encode(encrypt(data))

  print(enc)

  raise Exception("asdfasdfasdfasdfasdf")

def encrypt(data):
  cipher = AES.new(KEY, AES.MODE_ECB)
  return cipher.encrypt(data)

create_socket()
