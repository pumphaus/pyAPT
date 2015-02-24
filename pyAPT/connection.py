# -*- coding: utf-8 -*-
import pylibftdi
import time
import struct as st

from .message import Message
from . import message

class Connection(object):
  def __init__(self, serial_number = None):
    super(Connection, self).__init__()
    
    # this takes up to 2-3s:
    dev = pylibftdi.Device(mode='b', device_id=serial_number)
    dev.baudrate = 115200

    def _checked_c(ret):
      if not ret == 0:
        raise Exception(dev.ftdi_fn.ftdi_get_error_string())

    _checked_c(dev.ftdi_fn.ftdi_set_line_property(  8,   # number of bits
                                                    1,   # number of stop bits
                                                    0   # no parity
                                                    ))
    time.sleep(50.0/1000)

    dev.flush(pylibftdi.FLUSH_BOTH)

    time.sleep(50.0/1000)

    # skipping reset part since it looks like pylibftdi does it already

    # this is pulled from ftdi.h
    SIO_RTS_CTS_HS = (0x1 << 8)
    _checked_c(dev.ftdi_fn.ftdi_setflowctrl(SIO_RTS_CTS_HS))

    _checked_c(dev.ftdi_fn.ftdi_setrts(1))

    # the message queue are messages that are sent asynchronously. For example
    # if we performed a move, and are waiting for move completed message,
    # any other message received in the mean time are place in the queue.
    self.message_queue = []

    self.serial_number = serial_number
    self._device = dev
    
  def __enter__(self):
    return self

  def __exit__(self, type_, value, traceback):
    self.close()

  def __del__(self):
    self.close()

  def close(self):
    if not self._device.closed:
      print('Closing connnection to controller',self.serial_number)
      # XXX we might want a timeout here, or this will block forever
      self._device.close()

  def _send_message(self, m):
    """
    m should be an instance of Message, or has a pack() method which returns
    bytes to be sent to the controller
    """
    self._device.write(m.pack())

  def _read(self, length, block=True):
    """
    If block is True, then we will return only when have have length number of
    bytes. Otherwise we will perform a read, then immediately return with
    however many bytes we managed to read.

    Note that if no data is available, then an empty byte string will be
    returned.
    """
    data = bytes()
    while len(data) < length:
      diff = length - len(data)
      data += self._device.read(diff)
      if not block:
        break

      time.sleep(0.001)

    return data

  def _read_message(self):
    data = self._read(message.MGMSG_HEADER_SIZE)
    msg = Message.unpack(data, header_only=True)
    if msg.hasdata:
      data = self._read(msg.datalength)
      msglist = list(msg)
      msglist[-1] = data
      return Message._make(msglist)
    return msg

  def _wait_message(self, expected_messageID, expected_src):
    found = False
    while not found:
      m = self._read_message()
      found = m.messageID == expected_messageID and m.src == expected_src
      if found:
        return m
      else:
        self.message_queue.append(m)
