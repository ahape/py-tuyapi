#!/usr/bin/python3
from datetime import datetime
import time
import socket
import json
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import base64
import hashlib

"""
KEY = str(hashlib.md5(b"yGAdlopoPVldABfn")).encode("utf8")
xap7CuPc/SAeOjdjlCk8Xo3T5ouakCTpCBUOKVDVHPCz6T5l4QzOgnOwZylKwSy3tda3kfU0JGVv8ATwCRKOUMnzevuhNVb6bj55MJKgQy1Ss/5Io9yPW1kxWcvAa6LJ+bfjNNWAmvLtJTOdEsovwyHtP0Bgf91Rr+Pq+dEMMcw=

bytearray([0x6c ,0x1e, 0xc8, 0xe2, 0xbb, 0x9b ,0xb5, 0x9a, 0xb5, 0x0b, 0x0d, 0xaf, 0x64, 0x9b, 0x41, 0x0a])


{
  gwId: 'ebe0828eedb64aacc0wxvf',
  devId: 'ebe0828eedb64aacc0wxvf',
  t: '1656281006',
  dps: {},
  uid: 'ebe0828eedb64aacc0wxvf'
}

encrypted GET:
xap7CuPc/SAeOjdjlCk8Xo3T5ouakCTpCBUOKVDVHPCz6T5l4QzOgnOwZylKwSy3tda3kfU0JGVv8ATwCRKOUHstdvn06wiLnLCYL5P5NTwQvTt8P9zykyI7i3/TBz7ZzxhNVEUGgxlDUTM/lu38VCf8p/WSCmcGKARbqd0cBAw=

"""



LIV_RM_3 = "192.168.1.137"
LIV_RM_3_DEV_ID = "ebe0828eedb64aacc0wxvf"
PORT = 6668
SAMPLE_TS = 1656282001 # int(time.time())
BLOCK_SIZE = 2**10
B64_KEY = "MzIxNjZhMmQ3Yzg4MDI4Yg=="

EX_GET_PAYLOAD = '{"gwId":"ebe0828eedb64aacc0wxvf","devId":"ebe0828eedb64aacc0wxvf","t":1656282001,"dps":{},"uid":"ebe0828eedb64aacc0wxvf"}'
EX_SET_PAYLOAD = '{"devId":"ebe0828eedb64aacc0wxvf","gwId":"ebe0828eedb64aacc0wxvf","uid":"","t":1656282001,"dps":{"20":true,"21":"colour"}}'
B64_PAYLOAD = "eyJnd0lkIjoiZWJlMDgyOGVlZGI2NGFhY2Mwd3h2ZiIsImRldklkIjoiZWJlMDgyOGVlZGI2NGFhY2Mwd3h2ZiIsInQiOjE2NTYyODIwMDEsImRwcyI6e30sInVpZCI6ImViZTA4MjhlZWRiNjRhYWNjMHd4dmYifQ=="
ENC_PAYLOAD_B64 = "xap7CuPc/SAeOjdjlCk8Xo3T5ouakCTpCBUOKVDVHPCz6T5l4QzOgnOwZylKwSy3tda3kfU0JGVv8ATwCRKOUHstdvn06wiLnLCYL5P5NTwQvTt8P9zykyI7i3/TBz7ZzxhNVEUGgxlDUTM/lu38VCf8p/WSCmcGKARbqd0cBAw="
GET_PAYLOAD_FRAME = "[0,0,85,170,0,0,0,1,0,0,0,10,0,0,0,136,197,170,123,10,227,220,253,32,30,58,55,99,148,41,60,94,141,211,230,139,154,144,36,233,8,21,14,41,80,213,28,240,179,233,62,101,225,12,206,130,115,176,103,41,74,193,44,183,181,214,183,145,245,52,36,101,111,240,4,240,9,18,142,80,123,45,118,249,244,235,8,139,156,176,152,47,147,249,53,60,16,189,59,124,63,220,242,147,34,59,139,127,211,7,62,217,207,24,77,84,69,6,131,25,67,81,51,63,150,237,252,84,39,252,167,245,146,10,103,6,40,4,91,169,221,28,4,12,62,82,187,66,0,0,170,85]"
GET_CRC = 1045609282

def create_socket():
  with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    json_payload = {
      "gwId": LIV_RM_3_DEV_ID,
      "devId": LIV_RM_3_DEV_ID,
      "t": SAMPLE_TS,
      "dps": {}, # { "20": True, "21": "colour" },
      "uid": LIV_RM_3_DEV_ID,
    }

    msg = encode(json_payload)

    s.connect((LIV_RM_3, PORT))

    send_socket(s, msg)

    data = s.recv(BLOCK_SIZE)

    parse_packet(data)

def send_socket(sock, data):
  arr = bytearray(len(data) + 24)
  # Begin frame
  arr[0] = 0x00
  arr[1] = 0x00
  arr[2] = 0x55
  arr[3] = 0xAA
  # Sequence N
  arr[4 + 3] = 0x01
  # Command byte
  arr[8 + 3] = 0x0A
  # Payload length
  arr[12 + 3] = len(data) + 8
  # Payload
  arr[16:-8] = data
  # Calc CRC
  crc_i = len(data) + 16
  calc_crc = crc_32(arr[:crc_i]) & 0xFFFFFFFF

  assert(calc_crc == GET_CRC)

  # Write out CRC signature
  arr[crc_i + 0] = (calc_crc >> (4 * 6)) & 0xff
  arr[crc_i + 1] = (calc_crc >> (4 * 4)) & 0xff
  arr[crc_i + 2] = (calc_crc >> (4 * 2)) & 0xff
  arr[crc_i + 3] = (calc_crc >> (4 * 0)) & 0xff
  # End frame
  arr[len(data) + 20] = 0x00
  arr[len(data) + 21] = 0x00
  arr[len(data) + 22] = 0xAA
  arr[len(data) + 23] = 0x55

  to_assert = str([x for x in arr]).replace(" ", "")
  assert(GET_PAYLOAD_FRAME == to_assert)

  sock.sendall(arr)

def receive_socket(sock):
  chunk = sock.recv(BLOCK_SIZE)

  print(chunk)
  #return b"".join(chunk)


def encode(json_dict):
  data = json.dumps(json_dict).replace(" ", "")

  # Payloads are identical
  assert(data == EX_GET_PAYLOAD)

  b64data = base64.b64encode(data.encode("utf-8")).decode("utf-8")

  # Payload bytes are the same
  assert(b64data == B64_PAYLOAD)

  enc = encrypt(data)
  enc_b64 = base64.b64encode(enc).decode("utf-8")

  assert(enc_b64 == ENC_PAYLOAD_B64)

  return enc

def parse_packet(data):
  if len(data) < 24:
    raise Exception(f"Packet too short: {len(data)}")

  prefix = bytes_to_int32(data[:4])

  if prefix != 0x000055AA:
    raise Exception(f"Prefix not 0x000055AA: {prefix:02x}")

  suffix = bytes_to_int32(data[-4:])

  if suffix != 0x0000AA55:
    raise Exception(f"Suffix not 0x0000AA55: {suffix}")

  seq = bytes_to_int32(data[4:8])

  cmd = bytes_to_int32(data[8:12])

  size = bytes_to_int32(data[12:16])

  if len(data) - 8 < size:
    raise Exception(f"Payload missing: {size}")

  ret_code = bytes_to_int32(data[16:20])

  HEADER_SIZE = 16

  if ret_code & 0xFFFFFF00:
    payload = data[HEADER_SIZE: HEADER_SIZE + size - 8]
  else:
    payload = data[HEADER_SIZE + 4: HEADER_SIZE + size - 8]

  crc_start = HEADER_SIZE + size - 8
  expected = bytes_to_int32(data[crc_start:crc_start + 4])
  computed = crc_32(data[:size + 8])

  if expected != computed:
    raise Exception(f"CRCs don't match. Expected: {expected}, computed: {computed}")

  payload = json.loads(decrypt(payload))

  print(payload)


def encrypt(data):
  key = base64.b64decode(B64_KEY)
  cipher = AES.new(key, AES.MODE_ECB)
  encrypted = cipher.encrypt(pad(data.encode("utf-8"), AES.block_size))
  return encrypted

def decrypt(data):
  #data = data[15:]
  key = base64.b64decode(B64_KEY)
  cipher = AES.new(key, AES.MODE_ECB)
  decrypted = unpad(cipher.decrypt(data), AES.block_size)
  return decrypted

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

def bytes_to_int32(byte_arr):
  power = 0
  res = 0
  arr = list(byte_arr[:])
  arr.reverse()
  for b in arr:
    res += pow(2, power) * b
    power += 8

  return res


create_socket()


