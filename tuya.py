#!/usr/bin/python3

# NOTE
# Got rid of global options
# Got rid of shouldWaitForResponse

from datetime import datetime
import time
import socket

DATA_INVALID_RESPONSE = "json obj data unvalid"

class Device:
  def __init__(self, ip, port, id, key, productKey, gwID, version):
    self.ip = ip
    self.id = id
    self.port = port
    self.key = key
    self.productKey = productKey
    self.gwID = gwID or id
    self.version = version

class Emitter:
  def __init__(self):
    self._subs = {}

  def on(self, key, callback):
    if key not in self._subs:
      self._subs[key] = []

    self._subs[key].append(callback)

  def off(self):
    self._subs[key] = []

  def emit(self, key, arg):
    if key not in self._subs:
      print("Key not found -- cannot emit " % key)
      return

    for callback in self._subs[key]:
      callback(arg)

class Tuya(Emitter):
  def __init__(self,
      ip,
      port,
      id,
      key,
      productKey,
      gwID=None,
      version=3.1,
      nullPayloadOnJSONError=False,
      issueGetOnConnect=True,
      issueRefreshOnConnect=False):

    self.device = Device(ip, port, id, key, productKey, gwID, version)

    self.nullPayloadOnJSONError = nullPayloadOnJSONError

    # Check arguments
    if not id or not ip:
      raise Exception("ID and IP are missing from device.")

    # Check key
    if not key or len(key) != 16:
      raise Exception("Key is missing or incorrect.")

    # Handles encoding/decoding, encrypting/decrypting messages
    """
    self.device.parser = new MessageParser({
      key: self.device.key,
      version: self.device.version
    })
    """

    # Contains array of found devices when calling .find()
    self.foundDevices = []

    # Private instance variables

    # Socket connected state
    self._connected = False

    self._responseTimeout = 2
    self._connectTimeout = 5
    self._pingPongPeriod = 10
    self._pingPongTimeout = None
    self._lastPingAt = datetime.now()

    self._currentSequenceN = 0
    self._resolvers = {}
    """
    self._setQueue = new PQueue({
      concurrency: 1
    })
    """

    # List of dps which needed CommandType.DP_REFRESH (command 18) to force refresh their values.
    # Power data - DP 19 on some 3.1/3.3 devices, DP 5 for some 3.1 devices.
    self._dpRefreshIds = [4, 5, 6, 18, 19, 20]

  def get(self, options={}):
    payload = {
      "gwId": self.device.gwID,
      "devId": self.device.id,
      "t": str(int(time.time())),
      "dps": {},
      "uid": self.device.id
    }

    if "cid" in options:
      payload["cid"] = options["cid"]

    print("GET payload")
    print(payload)

    # Create byte buffer
    self._currentSequenceN += 1

    """
    buffer = self.device.parser.encode({
      data: payload,
      commandByte: CommandType.DP_QUERY,
      sequenceN: self._currentSequenceN
    })
    """
    # TODO
    buffer = payload

    data = self._send(buffer)

    if data == DATA_INVALID_RESPONSE:
      setOptions = {
        dps: options["dps"] if options["dps"] else 1,
        set: None,
      }
      self.set(setOptions)

    if data or "schema" in options and options["schema"] is True:
      return data

    if "dps" in options:
      return data["dps"][options["dps"]]

    # Default DPS key is "1"
    return data["dps"]["1"]

  def set(self, options={}):
    if "set" not in options:
      raise Exception("'set' not passed into options argument")

    if "multiple" in options:
      dps = options["data"]
    elif "dps" not in options:
      dps = { "1": options["set"] }
    else:
      dps = { str(options["dps"]): options["set"] }

    # Construct payload
    payload = {
      "t": int(time.time()),
      "dps": dps,
      "uid": "",
    }

    if "cid" in options:
      payload["cid"] = options["cid"]
    else:
      payload["devId"] = options["devId"] if "devId" in options else self.device.id
      payload["gwId"] = self.device.gwID

    print('SET Payload:')
    print(payload)

    # Encode into packet
    self._currentSequenceN += 1
    # TODO
    buffer = {}
    """
    buffer = self.device.parser.encode({
      data: payload,
      encrypted: true, # Set commands must be encrypted
      commandByte: CommandType.CONTROL,
      sequenceN: ++self._currentSequenceN
    })
    """

    data = self._send(buffer)

  def disconnect(self):
    if not self._connected:
      return

    # TODO .close() any sockets here
    print("Disconnecting...")

    self._connected = False

    self.client.close()

    self.emit("disconnected")

  def connect(self):
    if not self._connected:
      """
          resolvedOrRejected = False;
          self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

          # Attempt to connect
          print(f"Connecting to {self.device.ip}...")

          self.client.bind(self.device.ip, self.device.port);
          self.client.listen()

          # Default connect timeout is ~1 minute,
          # 5 seconds is a more reasonable default
          # since `retry` is used.
          self.client.setTimeout(self._connectTimeout * 1000, () => {
            # self.emit('error', new Error('connection timed out'));
            self.client.destroy();
            self.emit('error', new Error('connection timed out'));
            if (!resolvedOrRejected) {
              reject(new Error('connection timed out'));
              resolvedOrRejected = true;
            }
          });

          # Add event listeners to socket

          # Parse response data
          self.client.on('data', data => {
            debug(`Received data: ${data.toString('hex')}`);

            let packets;

            try {
              packets = self.device.parser.parse(data);

              if (self.nullPayloadOnJSONError) {
                for (const packet of packets) {
                  if (packet.payload && packet.payload === 'json obj data unvalid') {
                    self.emit('error', packet.payload);

                    packet.payload = {
                      dps: {
                        1: null,
                        2: null,
                        3: null,
                        101: null,
                        102: null,
                        103: null
                      }
                    };
                  }
                }
              }
            } catch (error) {
              debug(error);
              self.emit('error', error);
              return;
            }

            packets.forEach(packet => {
              debug('Parsed:');
              debug(packet);

              self._packetHandler.bind(self)(packet);
            });
          });

          # Handle errors
          self.client.on('error', err => {
            debug('Error event from socket.', self.device.ip, err);

            self.emit('error', new Error('Error from socket: ' + err.message));

            if (!self._connected && !resolvedOrRejected) {
              reject(err);
              resolvedOrRejected = true;
            }

            self.client.destroy();
          });

          # Handle socket closure
          self.client.on('close', () => {
            debug(`Socket closed: ${self.device.ip}`);

            self.disconnect();
          });

          self.client.on('connect', async () => {
            debug('Socket connected.');

            self._connected = true;

            # Remove connect timeout
            self.client.setTimeout(0);

            /**
             * Emitted when socket is connected
             * to device. self event may be emitted
             * multiple times within the same script,
             * so don't use self as a trigger for your
             * initialization code.
             * @event TuyaDevice#connected
             */
            self.emit('connected');

            # Periodically send heartbeat ping
            self._pingPongInterval = setInterval(async () => {
              await self._sendPing();
            }, self._pingPongPeriod * 1000);

            # Automatically ask for dp_refresh so we
            # can emit a `dp_refresh` event as soon as possible
            if (self.globalOptions.issueRefreshOnConnect) {
              self.refresh();
            }

            # Automatically ask for current state so we
            # can emit a `data` event as soon as possible
            if (self.globalOptions.issueGetOnConnect) {
              self.get();
            }

            # Return
            if (!resolvedOrRejected) {
              resolve(true);
              resolvedOrRejected = true;
            }
          });
        });
      }
      """
      self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

      self.client.connect(("192.168.1.137", 6668))

      msg = self.encodeSocketMessage({
        'gwId': 'ebe0828eedb64aacc0wxvf',
        'devId': 'ebe0828eedb64aacc0wxvf',
        't': str(int(time.time())),
        'dps': {},
        'uid': 'ebe0828eedb64aacc0wxvf'
      })

      self.client.sendall(msg)

      data = self.client.recv(1024)

      print(f"Received {data!r}")

      self.client.close()

    # Return if already connected
    print("Already connected")
    return True

  def encodeSocketMessage(self, payload):
    payload = encrypt(payload)
    buffer = Buffer.alloc(len(payload) + 15)
    Buffer.from('3.3').copy(buffer, 0)
    payload.copy(buffer, 15)
    payload = buffer
    buffer = Buffer.alloc(payload.length + 24);

    # Add prefix, command, and length
    buffer.writeUInt32BE(0x000055AA, 0);
    buffer.writeUInt32BE(options.commandByte, 8);
    buffer.writeUInt32BE(payload.length + 8, 12);

    if (options.sequenceN) {
      buffer.writeUInt32BE(options.sequenceN, 4);
    }

    # Add payload, crc, and suffix
    payload.copy(buffer, 16);
    calculatedCrc = crc(buffer.slice(0, payload.length + 16)) & 0xFFFFFFFF;

    buffer.writeInt32BE(calculatedCrc, payload.length + 16);
    buffer.writeUInt32BE(0x0000AA55, payload.length + 20);

    return buffer;

  def isConnected(self):
    return self._connected

  def _send(self, buffer):
    return { "dps": "asdf" }
