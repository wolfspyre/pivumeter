#!/usr/bin/env python

import pivumeter
import signal
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
        self.running = True
        while self.running:
            try:
                message = self.messages.get(False)
                self.busy = True
                scrollphat.clear()
                scrollphat.write_string(message, 11)
                length = scrollphat.buffer_len()
                scrollphat.set_pixel(length + 11, 0, 0)
                #scrollphat.show()
                scrollphat.update()
                time.sleep(1)
                for x in range(length):
                    if not self.running: break
                    scrollphat.scroll(1)
                    #scrollphat.show()
                    scrollphat.update()
                    time.sleep(0.05)

                scrollphat.clear()
                self.messages.task_done()
                self.busy = False
            except queue.Empty:
                pass
            except IndexError:
                pass
            time.sleep(1)

    def setup(self):
        pass

    def display_fft(self, bins):
        print("display_vu was Called %s %s",left,right, bins)
        if self.busy: return
        self.busy = True
        #print(bins)
        # scrollphathd syntax:
        # scrollphathd.set_graph(bins, low=0, high=65535, brightness=1.0, x=0, y=0)
        # scrollphat graph is only 8bit (0-255)
        # https://stackoverflow.com/questions/17174407/what-is-an-efficient-way-to-scale-a-int16-numpy-array-to-a-int8-numpy-array
        #
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
        #print(_scaled_bins)
        scrollphat.graph(_scaled_bins, low=1, high=255)
        scrollphat.update()
        self.busy = False

    def display_vu(self, left, right, bins):
        print("display_vu was Called %s %s",left,right, bins)
        _paddingVal = 1
        _i=0
        _minVal=0
        _maxVal=65535
        while _i < 11:
            _i+1
            _mono = ( left[_i] + right[_i] / 2 )
            _scaled_bins.append(int(255.0 * (_mono - _minVal) / (_maxVal - _minVal - 1.0 + _paddingVal)))
        #pad if necessary
        #_scaled_bins[bins == _paddingVal] = 0
        #print(_scaled_bins)
        scrollphat.graph(_scaled_bins, low=1, high=255)
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
            ptype = data.find('type').text
            pcode = data.find('code').text
            payload = data.find('data')
            if payload is not None and payload.get('encoding') == 'base64':
                payload = decodestring(payload.text)
                print("GotData:", payload)

            # Song title
            if ptype == '636f7265' and pcode == '6d696e6d':
                print("Song Title: ",payload.strip())
                if payload.strip() != last_song:
                    print("sending payload to output_device: ",payload.strip())
                    output_device.messages.put(payload.strip())
                    last_song = payload

        except os.error as e:
            if e.errno == 11:
                os.close(f)
                continue

            raise e

        os.close(f)
        time.sleep(0.001)


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