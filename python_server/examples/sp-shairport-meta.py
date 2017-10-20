#!/usr/bin/env python

import pivumeter
import scrollphat
import threading
import time

import os

from base64 import decodestring
from xml.etree import ElementTree

try:
    import queue
except ImportError:
    import Queue as queue

class OutputScrollPhat(pivumeter.OutputDevice):
    def __init__(self):
        super(OutputScrollPhat, self).__init__()

        self.running = False
        self.busy = False
        scrollphat.set_brightness(2)
        self.messages = queue.Queue()

        self._thread = threading.Thread(target=self.run_messages)
        self._thread.daemon = True
        self._thread.start()

    def run_messages(self):
        pivumeter.log("run_messages: called",level=1)
        self.running = True
        while self.running:
            try:
                message = self.messages.get(False)
                self.busy = True
                _msglen = len(message)
                scrollphat.clear()
                if _msglen <= 3:
                    #string doesn't needs
                    scrollphat.write_string(message)
                    scrollphat.update()
                    time.sleep(0.75)
                else:
                    pivumeter.log("Sending to scroll ({}): {}".format(_msglen, message),level=3)
                    #prepend with 11 spaces for scrolling
                    scrollphat.write_string(message, 11)
                    length = scrollphat.buffer_len()
                    pivumeter.log("Length: {}".format(length),level=3)
                    scrollphat.update()
                    time.sleep(0.25)
                    for x in range(length):
                        #pivumeter.log("{}".format(x),level=4)
                        if not self.running: break
                        scrollphat.scroll()
                        scrollphat.update()
                        time.sleep(0.04)
                    #pivumeter.log("Done",level=3)
                scrollphat.clear()
                self.messages.task_done()
                self.busy = False
            except queue.Empty:
                pass
            except IndexError:
                pass
            time.sleep(0.4)

    def setup(self):
        pass

    def display_fft(self, bins):
        if self.busy: return
        self.busy = True
        #print(bins)
        # scrollphathd syntax:
        # scrollphathd.set_graph(bins, low=0, high=65535, brightness=1.0, x=0, y=0)
        # scrollphat graph is only 8bit (0-255)
        # https://stackoverflow.com/questions/17174407/what-is-an-efficient-way-to-scale-a-int16-numpy-array-to-a-int8-numpy-array
        #
        # https://github.com/CellProfiler/CellProfiler/issues/2285 #
        _paddingVal = 1
        _i=0
        _minVal=0
        _maxVal=65535
        _scaled_bins = []
        for _led in bins:
            _scaled_bins.append(int(255.0 * (_led - _minVal) / (_maxVal - _minVal - 1.0 + _paddingVal)))
        #        _scaled_bins = (255.0 * (bins - 1) / (65535 - 1 - 1.0)).astype(uint8)
        #pad if necessary
        #_scaled_bins[bins == _paddingVal] = 0
        #pivumeter.log("display_fft: {}".format(_scaled_bins),level=0)
        scrollphat.graph(_scaled_bins, low=1, high=255)
        scrollphat.update()
        self.busy = False

    def display_vu(self, left, right):
        #This is called with every datapoint.
        # pivumeter.log("display_vu was called",4)
        _paddingVal = 1
        _i=0
        _minVal=0
        _maxVal=65535
        _scaled_bins = []
        #print("Moo ",left,right, _mono)
        #while _i < 1:
        #    _i = _i+1
        #    _scaled_bins.append(int(255.0 * (_mono - _minVal) / (_maxVal - _minVal - 1.0 + _paddingVal)))
        #    #pad if necessary
        #    #_scaled_bins[bins == _paddingVal] = 0
        #    print(_scaled_bins)
        #    scrollphat.graph(_scaled_bins, low=1, high=255)
        pass

    def cleanup(self):
        self.running = False
        self._thread.join()

print("""
Press Ctrl+C then hit Enter to exit.
""")

output_device = OutputScrollPhat()

pivumeter.run(output_device)

try:
    last_song = None

    while pivumeter.running:
        f = os.open('/tmp/shairport-sync-metadata', os.O_RDONLY|os.O_NONBLOCK)

        try:
            buf = ''
            while True:
                c = os.read(f, 1)
                buf += c
                if buf.endswith("</item>"):
                    break


            data = ElementTree.fromstring(buf)
            #print(buf)
            # https://github.com/wolfspyre/shairport-sync-metadata-reader

            ptype = data.find('type').text
            pcode = data.find('code').text
            payload = data.find('data')
            if payload is not None and payload.get('encoding') == 'base64':
                payload = decodestring(payload.text)
                _type = decodestring(ptype)
                _code = decodestring(pcode)
                pivumeter.log("GotData: [{}] [[{}]] : {}".format(ptype, pcode, payload),level=3)


            # Song title
            if ptype == '636f7265' and pcode == '6d696e6d':
                pivumeter.log("Song Title: {}".format(payload.strip()),level=3)
                if payload.strip() != last_song:
                    pivumeter.log("sending payload to output_device: {}".format(payload.strip()),level=3)
                    output_device.messages.put(payload.strip())
                    last_song = payload
            elif ptype == 'localmsg':
                if pcode == 'test' and payload is not None:
                    _p=payload.text
                    pivumeter.log("RX TEST {}".format(_p),level=3)
                    output_device.messages.put(_p)
                else:
                    pivumeter.log("RX TEST but no payload",level=2)

        except os.error as e:
            if e.errno == 11:
                os.close(f)
                continue

            raise e

        os.close(f)
        time.sleep(0.005)


#        # other messages
#        f = os.open('/tmp/scrollphat_data', os.O_RDONLY|os.O_NONBLOCK)
#        try:
#            buf = ''
#            while True:
#                c = os.read(f, 1)
#                buf += c
#                if buf.endswith("</item>"):
#                    break
#
#            data = ElementTree.fromstring(buf)
#            print(buf)
#            ptype = data.find('type').text
#            pcode = data.find('code').text
#            payload = data.find('data')
#            if payload is not None and payload.get('encoding') == 'base64':
#                payload = decodestring(payload.text)
#
#                # Song title
#            if ptype == '636f7265' and pcode == '6d696e6d':
#                if payload.strip() != last_song:
#                    output_device.messages.put(payload.strip())
#                    last_song = payload
#        except os.error as e:
#            if e.errno == 11:
#                os.close(f)
#                continue
#            raise e
#
#        os.close(f)
#        time.sleep(0.001)
except KeyboardInterrupt:
    pass