#!/usr/bin/python3
import base64
import json
import socket
import time
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import test_data
import sys
import os

SOCKET_PORT = 6668
SOCKET_BLOCK_SIZE = 1024 # Should be large enough for our small messages
MESSAGE_HEADER_SIZE = 16

DEBUG = os.getenv("DEBUG") == "true"

is_post = True

def send_device_request(dev=None):
  # TODO: Pass in options that determine what sort of payload to create
  # Create payload
  if DEBUG:
    key = test_data.LIV_RM_3_KEY.encode("utf-8")
    payload = test_data.SET_PAYLOAD if is_post else test_data.GET_PAYLOAD
    dev = test_data.LIV_RM_3
  else:
    key = dev["key"].encode("utf-8")
    payload = create_json_payload(dev)

  # Encrypt payload
  enc_payload = encrypt_json_payload(payload, key)

  # Serialize payload into bytes
  message = create_socket_message(enc_payload)

  print(f"Connecting to {dev['name']} ({dev['ip']}) ...")

  # Send message ... synchronously await response
  enc_response = send_socket_message(message, dev["ip"], key)

  # Decrypt encrypted response
  response = decrypt_json_payload(enc_response, key)

  print(f"Received data from {dev['name']}", response)

def create_json_payload(dev):
  if is_post:
    return {
      "devId": dev["id"],
      "gwId": dev["id"],
      "uid": "",
      "t": int(time.time()),
      "dps": {
        "20": True,
        "21": "colour",
        "24": colors[color_index],
      },
    }
  else:
    return {
      "devId": dev["id"],
      "gwId": dev["id"],
      "uid": dev["id"],
      "t": int(time.time()),
      "dps": {},
    }

def encrypt_json_payload(json_dict, key):
  # Compress our JSON string as small as we can
  data = json.dumps(json_dict).replace(" ", "")

  if DEBUG:
    if is_post:
      assert test_data.SET_PAYLOAD_B64 == get_b64(data.encode("utf-8"))
    else:
      assert test_data.GET_PAYLOAD_B64 == get_b64(data.encode("utf-8"))

  cipher = AES.new(key, AES.MODE_ECB)
  enc = cipher.encrypt(pad(data.encode("utf-8"), AES.block_size))

  if DEBUG:
    if is_post:
      assert test_data.ENC_SET_PAYLOAD_NO_VERSION_HEADER_B64 == get_b64(enc)
    else:
      assert test_data.ENC_GET_PAYLOAD_B64 == get_b64(enc)

  if is_post:
    tmp = bytearray(len(enc) + 15)
    tmp[15:] = enc
    prefix = b"3.3"
    tmp[0:len(prefix)] = prefix
    enc = tmp

    if DEBUG:
      assert test_data.ENC_SET_PAYLOAD_B64 == get_b64(enc)

  return enc

def decrypt_json_payload(data, key):
  if is_post:
    data = data[15:]

  cipher = AES.new(key, AES.MODE_ECB)

  try:
    decrypted = unpad(cipher.decrypt(data), AES.block_size)
  except:
    print("ERROR: Unable to connect to device")
    return

  try:
    return json.loads(decrypted)
  except:
    print("ERROR: Couldn't parse as JSON", decrypted)

def create_socket_message(data):
  data_len = len(data)
  arr = bytearray(data_len + 24)
  # Begin frame
  arr[:3] = [0x00, 0x00, 0x55, 0xAA]
  # Sequence N
  arr[7] = 0x01
  # Command byte
  arr[11] = 0x07 if is_post else 0x0a
  # Payload length
  arr[15] = data_len + 8
  # Payload
  arr[16:-8] = data
  # Calc CRC
  crc_i = data_len + 16
  calc_crc = crc_32(arr[:crc_i]) & 0xFFFFFFFF

  if DEBUG and not is_post:
    assert calc_crc == test_data.GET_CRC

  # Write out CRC signature
  arr[crc_i + 0] = (calc_crc >> 0x18) & 0xff
  arr[crc_i + 1] = (calc_crc >> 0x10) & 0xff
  arr[crc_i + 2] = (calc_crc >> 0x08) & 0xff
  arr[crc_i + 3] = (calc_crc >> 0x00) & 0xff
  # End frame
  arr[data_len + 20:] = [0x00, 0x00, 0xAA, 0x55]

  if DEBUG and not is_post:
    assert test_data.GET_PAYLOAD_FRAME == str(list(arr)).replace(" ", "")

  return arr

def send_socket_message(message, dev_ip, key):
  with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    if DEBUG:
      s.connect((test_data.LIV_RM_3_IP, SOCKET_PORT))
    else:
      s.connect((dev_ip, SOCKET_PORT))

    s.sendall(message)

    response = s.recv(SOCKET_BLOCK_SIZE)

  return parse_socket_response(response, key)

def parse_socket_response(data, key):
  if len(data) < 24:
    raise Exception(f"Packet too short: {len(data)}")

  prefix = int.from_bytes(data[:4], "big")

  if prefix != 0x000055AA:
    raise Exception(f"Prefix not 0x000055AA: {prefix:02x}")

  suffix = int.from_bytes(data[-4:], "big")

  if suffix != 0x0000AA55:
    raise Exception(f"Suffix not 0x0000AA55: {suffix}")

  seq = int.from_bytes(data[4:8], "big")

  cmd = int.from_bytes(data[8:12], "big")

  size = int.from_bytes(data[12:16], "big")

  if len(data) - 8 < size:
    raise Exception(f"Payload missing: {size}")

  ret_code = int.from_bytes(data[16:20], "big")

  if ret_code & 0xFFFFFF00:
    payload = data[MESSAGE_HEADER_SIZE: MESSAGE_HEADER_SIZE + size - 8]
  else:
    payload = data[MESSAGE_HEADER_SIZE + 4: MESSAGE_HEADER_SIZE + size - 8]

  crc_start = MESSAGE_HEADER_SIZE + size - 8
  expected = int.from_bytes(data[crc_start:crc_start + 4], "big")
  computed = crc_32(data[:size + 8])

  if expected != computed:
    raise Exception(f"CRCs don't match. Expected: {expected}, computed: {computed}")

  return payload

crc_32_table = [
  0x00000000, 0x77073096, 0xEE0E612C, 0x990951BA,
  0x076DC419, 0x706AF48F, 0xE963A535, 0x9E6495A3,
  0x0EDB8832, 0x79DCB8A4, 0xE0D5E91E, 0x97D2D988,
  0x09B64C2B, 0x7EB17CBD, 0xE7B82D07, 0x90BF1D91,
  0x1DB71064, 0x6AB020F2, 0xF3B97148, 0x84BE41DE,
  0x1ADAD47D, 0x6DDDE4EB, 0xF4D4B551, 0x83D385C7,
  0x136C9856, 0x646BA8C0, 0xFD62F97A, 0x8A65C9EC,
  0x14015C4F, 0x63066CD9, 0xFA0F3D63, 0x8D080DF5,
  0x3B6E20C8, 0x4C69105E, 0xD56041E4, 0xA2677172,
  0x3C03E4D1, 0x4B04D447, 0xD20D85FD, 0xA50AB56B,
  0x35B5A8FA, 0x42B2986C, 0xDBBBC9D6, 0xACBCF940,
  0x32D86CE3, 0x45DF5C75, 0xDCD60DCF, 0xABD13D59,
  0x26D930AC, 0x51DE003A, 0xC8D75180, 0xBFD06116,
  0x21B4F4B5, 0x56B3C423, 0xCFBA9599, 0xB8BDA50F,
  0x2802B89E, 0x5F058808, 0xC60CD9B2, 0xB10BE924,
  0x2F6F7C87, 0x58684C11, 0xC1611DAB, 0xB6662D3D,
  0x76DC4190, 0x01DB7106, 0x98D220BC, 0xEFD5102A,
  0x71B18589, 0x06B6B51F, 0x9FBFE4A5, 0xE8B8D433,
  0x7807C9A2, 0x0F00F934, 0x9609A88E, 0xE10E9818,
  0x7F6A0DBB, 0x086D3D2D, 0x91646C97, 0xE6635C01,
  0x6B6B51F4, 0x1C6C6162, 0x856530D8, 0xF262004E,
  0x6C0695ED, 0x1B01A57B, 0x8208F4C1, 0xF50FC457,
  0x65B0D9C6, 0x12B7E950, 0x8BBEB8EA, 0xFCB9887C,
  0x62DD1DDF, 0x15DA2D49, 0x8CD37CF3, 0xFBD44C65,
  0x4DB26158, 0x3AB551CE, 0xA3BC0074, 0xD4BB30E2,
  0x4ADFA541, 0x3DD895D7, 0xA4D1C46D, 0xD3D6F4FB,
  0x4369E96A, 0x346ED9FC, 0xAD678846, 0xDA60B8D0,
  0x44042D73, 0x33031DE5, 0xAA0A4C5F, 0xDD0D7CC9,
  0x5005713C, 0x270241AA, 0xBE0B1010, 0xC90C2086,
  0x5768B525, 0x206F85B3, 0xB966D409, 0xCE61E49F,
  0x5EDEF90E, 0x29D9C998, 0xB0D09822, 0xC7D7A8B4,
  0x59B33D17, 0x2EB40D81, 0xB7BD5C3B, 0xC0BA6CAD,
  0xEDB88320, 0x9ABFB3B6, 0x03B6E20C, 0x74B1D29A,
  0xEAD54739, 0x9DD277AF, 0x04DB2615, 0x73DC1683,
  0xE3630B12, 0x94643B84, 0x0D6D6A3E, 0x7A6A5AA8,
  0xE40ECF0B, 0x9309FF9D, 0x0A00AE27, 0x7D079EB1,
  0xF00F9344, 0x8708A3D2, 0x1E01F268, 0x6906C2FE,
  0xF762575D, 0x806567CB, 0x196C3671, 0x6E6B06E7,
  0xFED41B76, 0x89D32BE0, 0x10DA7A5A, 0x67DD4ACC,
  0xF9B9DF6F, 0x8EBEEFF9, 0x17B7BE43, 0x60B08ED5,
  0xD6D6A3E8, 0xA1D1937E, 0x38D8C2C4, 0x4FDFF252,
  0xD1BB67F1, 0xA6BC5767, 0x3FB506DD, 0x48B2364B,
  0xD80D2BDA, 0xAF0A1B4C, 0x36034AF6, 0x41047A60,
  0xDF60EFC3, 0xA867DF55, 0x316E8EEF, 0x4669BE79,
  0xCB61B38C, 0xBC66831A, 0x256FD2A0, 0x5268E236,
  0xCC0C7795, 0xBB0B4703, 0x220216B9, 0x5505262F,
  0xC5BA3BBE, 0xB2BD0B28, 0x2BB45A92, 0x5CB36A04,
  0xC2D7FFA7, 0xB5D0CF31, 0x2CD99E8B, 0x5BDEAE1D,
  0x9B64C2B0, 0xEC63F226, 0x756AA39C, 0x026D930A,
  0x9C0906A9, 0xEB0E363F, 0x72076785, 0x05005713,
  0x95BF4A82, 0xE2B87A14, 0x7BB12BAE, 0x0CB61B38,
  0x92D28E9B, 0xE5D5BE0D, 0x7CDCEFB7, 0x0BDBDF21,
  0x86D3D2D4, 0xF1D4E242, 0x68DDB3F8, 0x1FDA836E,
  0x81BE16CD, 0xF6B9265B, 0x6FB077E1, 0x18B74777,
  0x88085AE6, 0xFF0F6A70, 0x66063BCA, 0x11010B5C,
  0x8F659EFF, 0xF862AE69, 0x616BFFD3, 0x166CCF45,
  0xA00AE278, 0xD70DD2EE, 0x4E048354, 0x3903B3C2,
  0xA7672661, 0xD06016F7, 0x4969474D, 0x3E6E77DB,
  0xAED16A4A, 0xD9D65ADC, 0x40DF0B66, 0x37D83BF0,
  0xA9BCAE53, 0xDEBB9EC5, 0x47B2CF7F, 0x30B5FFE9,
  0xBDBDF21C, 0xCABAC28A, 0x53B39330, 0x24B4A3A6,
  0xBAD03605, 0xCDD70693, 0x54DE5729, 0x23D967BF,
  0xB3667A2E, 0xC4614AB8, 0x5D681B02, 0x2A6F2B94,
  0xB40BBE37, 0xC30C8EA1, 0x5A05DF1B, 0x2D02EF8D,
]


def crc_32(byte_arr):
  max_32 = 0xFFFFFFFF
  crc = max_32

  for b in byte_arr:
    crc = (crc >> 8) ^ crc_32_table[(crc ^ b) & 0xFF]

  return crc ^ max_32

def get_b64(data):
  return base64.b64encode(data).decode("utf-8")

if __name__ == "__main__":
  if DEBUG:
    # Test GET
    is_post = False
    send_device_request()

    # Test SET
    is_post = True
    send_device_request()
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
        send_device_request(dev)
