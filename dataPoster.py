import requests
import pandas as pd
import datetime
    
url = "http://localhost.com/api"

import asyncio
from bleak import BleakScanner, BleakClient, BLEDevice
import time
import ctypes
import struct

import collections

import sys
from math import sin
from threading import Thread
from time import sleep
from asyncqt import QEventLoop


from PyQt5 import QtCore, QtGui, QtWidgets
from pglive.kwargs import Axis
from pglive.sources.data_connector import DataConnector
from pglive.sources.live_axis import LiveAxis
from pglive.sources.live_plot import LiveLinePlot
from pglive.sources.live_plot_widget import LivePlotWidget

sleepMask = None
UUID_MANUFACTURER = "00002a29-0000-1000-8000-00805f9b34fb"
UUID_MODEL_NUMBER = "00002a24-0000-1000-8000-00805f9b34fb"
UUID_SERIAL_NUMBER = "00002a25-0000-1000-8000-00805f9b34fb"
UUID_FIRMWARE_REVISION ="00002a26-0000-1000-8000-00805f9b34fb"

UUID_BATTERY_LEVEL = "00002a19-0000-1000-8000-00805f9b34fb"

UUID_MASK_READ = "00000011-0000-1000-8000-00805f9b34fb"
UUID_MASK_CMD = "00000021-0000-1000-8000-00805f9b34fb"

# Graphing Variables
EVENT_QUEUE_SIZE = 10
MATCH_QUEUE_SIZE = 10
BUFFER_SIZE = 128
DATA_GROUPS = 7
NUM_BUFFER_TYPES = 7
EPOCH_PERIOD = 1000
DATA_LENGTH = DATA_GROUPS * NUM_BUFFER_TYPES

# Sleep Executive Command
CMD_START_BURST_READ = bytearray(b'\x00')
CMD_PEAK_BUFFER = bytearray(b'\x01')
CMD_LED_CONTROL = bytearray(b'\x02')
CMD_TOGGLE_SAMPLING = bytearray(b'\x03')

# Mask Data Buffers
BUFFER_SYNC = bytearray(b'\x00')

tick_buffer = collections.deque(maxlen=BUFFER_SIZE, iterable=(0,0))
eog_buffer = collections.deque(maxlen=BUFFER_SIZE, iterable=(0,0))
accelx_buffer = collections.deque(maxlen=BUFFER_SIZE, iterable=(0,0))
accely_buffer = collections.deque(maxlen=BUFFER_SIZE, iterable=(0,0))
accelz_buffer = collections.deque(maxlen=BUFFER_SIZE, iterable=(0,0))
heartred_buffer = collections.deque(maxlen=BUFFER_SIZE, iterable=(0,0))
heartir_buffer = collections.deque(maxlen=BUFFER_SIZE, iterable=(0,0))

running = True
firstRecorded = False

# Will create connection to SleepMask and signal data has changed
# Handles SleepMask connection states
class BLEHandler(QtCore.QObject):
    dataChanged = QtCore.pyqtSignal(int)
    _transport = None
    packet_counter = 0

    def __init__(self, parent=None):
        super().__init__(parent)
        self._transport = None
        self.packet_counter = 0
        self.sleepMaskDevice = None # Handler for BLE
        self.connectionContext = None # Connection context
        self.is_connected = False
        self.is_recording = False

        # SleepMask MetaData
        self.model_number = ""
        self.manufacturer = ""
        self.firmware_version = ""
        self.serial_number = ""
        self.battery_level = ""

        # Init buffers


    async def init_connection(self):
        devices = await BleakScanner.discover()
        for d in devices:
            if(d.name == "Hypnogogia Mask"):
                print("Found Sleep Mask!")
                self.sleepMaskDevice = d
                self.connectionContext = BleakClient(self.sleepMaskDevice.address)
                try:
                    print("Pairing!")
                    await self.connectionContext.connect()
                    self.is_connected = True
                    await self.read_mask_info()
                except Exception as e:
                    self.is_connected = False
                    print(f"Could not pair. {str(e)}")
                    break
                break

    async def del_connection(self):
        if(not self.is_connected):
            print("Already disconnected")
            return
        try:
            await self.connectionContext.disconnect()
            self.is_connected = False
        except Exception as e:
            print(f"Could not unpair. {str(e)}")

    async def read_mask_info(self):
        if(not self.is_connected):
            print(f"Mask isnt connected.")
            return
        
        self.model_number = await self.connectionContext.read_gatt_char(UUID_MODEL_NUMBER)
        self.manufacturer = await self.connectionContext.read_gatt_char(UUID_MANUFACTURER)
        self.firmware_version = await self.connectionContext.read_gatt_char(UUID_FIRMWARE_REVISION)
        self.serial_number = await self.connectionContext.read_gatt_char(UUID_SERIAL_NUMBER)
        self.battery_level = await self.connectionContext.read_gatt_char(UUID_BATTERY_LEVEL)

        print("=====DEVICE INFO=====")
        print("Model Number: {0}".format("".join(map(chr, self.model_number))))
        print("Manufacturer: {0}".format("".join(map(chr, self.manufacturer))))
        print("Firmware Version: {0}".format("".join(map(chr, self.firmware_version))))
        print("Serial Number: {0}".format("".join(map(chr, self.serial_number))))
        print("Current Battery Level: {0}".format("".join(map(chr, self.battery_level))))
        print("=====================")

    async def toggle_sampling(self):
        await self.connectionContext.write_gatt_char(UUID_MASK_CMD, CMD_TOGGLE_SAMPLING, response=False)
        return_code = int.from_bytes((await self.connectionContext.read_gatt_char(UUID_MASK_CMD)), "little", signed="False")
        if(return_code != 0):
            print(f"Error Toggling Sampling: {return_code}")

    async def read_data_buffer(self, buf_sel, printing=False):
        await self.connectionContext.write_gatt_char(UUID_MASK_CMD, (CMD_START_BURST_READ + buf_sel), response=False)
        return_code = int.from_bytes((await self.connectionContext.read_gatt_char(UUID_MASK_CMD)), "little", signed="False")
        if(return_code != 0):
            print(f"Error Starting Burst Read: {return_code}")
            return
        buffersize = int.from_bytes((await self.connectionContext.read_gatt_char(UUID_MASK_READ)), "little", signed="False")
        for x in range(0,buffersize):
            data = await self.connectionContext.read_gatt_char(UUID_MASK_READ)
            
            if(printing):
                print(f"Buffer {x}: {data}")
                print(f"Buffer Length {x}: {str(len(data))}")
            # Unpack into unsigned integers
            data_unpacked = struct.unpack((str(DATA_LENGTH)+'I'), data)
            self.data_into_buffer(data_unpacked)

    def data_into_buffer(self, data):
        global tick_buffer
        global eog_buffer
        global accelx_buffer
        global accely_buffer
        global accelz_buffer
        global heartir_buffer
        global heartred_buffer

        # Group integers into buffer types 
        for group in range(0, DATA_GROUPS):
            tick = data[0 + (NUM_BUFFER_TYPES * group)]
            eog_buffer.append(([data[1 + (NUM_BUFFER_TYPES * group)], tick]))
            accelx_buffer.append(([data[2 + (NUM_BUFFER_TYPES * group)], tick]))
            accely_buffer.append(([data[3 + (NUM_BUFFER_TYPES * group)], tick]))
            accelz_buffer.append(([data[4 + (NUM_BUFFER_TYPES * group)], tick]))
            heartred_buffer.append(([data[5 + (NUM_BUFFER_TYPES * group)], tick]))
            heartir_buffer.append(([data[6 + (NUM_BUFFER_TYPES * group)], tick]))
        # Add the tick marker

    async def start_recording(self):
        if(not self.is_connected):
            print("Cannot Record, Mask is not connected")
        
        await self.toggle_sampling()
        self.is_recording = True
        while (self.is_recording):
            await self.read_data_buffer(BUFFER_SYNC)
        await self.toggle_sampling()

    async def stop_recording(self):
        if(not self.is_connected):
            print("Cannot Stop Recoding, Mask is not connected")
        self.is_recording = False

class GraphWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.eog_plot_widget = LivePlotWidget(title="EOG @ 144Hz")
        self.eog_plot_curve = LiveLinePlot()
        self.eog_plot_widget.addItem(self.eog_plot_curve)
        self.eog_data_connector = DataConnector(self.eog_plot_curve, max_points=600, update_rate=144)
        mainLayout = QtWidgets.QVBoxLayout(self)
        mainLayout.addWidget(self.eog_plot_widget)

        self.ax_plot_widget = LivePlotWidget(title="Accel X @ 144Hz")
        self.ax_plot_curve = LiveLinePlot()
        self.ax_plot_widget.addItem(self.ax_plot_curve)
        self.ax_data_connector = DataConnector(self.ax_plot_curve, max_points=600, update_rate=144)
        mainLayout.addWidget(self.ax_plot_widget)

        self.ay_plot_widget = LivePlotWidget(title="Accel Y @ 144Hz")
        self.ay_plot_curve = LiveLinePlot()
        self.ay_plot_widget.addItem(self.ay_plot_curve)
        self.ay_data_connector = DataConnector(self.ay_plot_curve, max_points=600, update_rate=144)
        mainLayout.addWidget(self.ay_plot_widget)

        self.az_plot_widget = LivePlotWidget(title="Accel Z @ 144Hz")
        self.az_plot_curve = LiveLinePlot()
        self.az_plot_widget.addItem(self.az_plot_curve)
        self.az_data_connector = DataConnector(self.az_plot_curve, max_points=600, update_rate=144)
        mainLayout.addWidget(self.az_plot_widget)

        self.red_plot_widget = LivePlotWidget(title="Red Light @ 144Hz")
        self.red_plot_curve = LiveLinePlot()
        self.red_plot_widget.addItem(self.red_plot_curve)
        self.red_data_connector = DataConnector(self.red_plot_curve, max_points=600, update_rate=144)
        mainLayout.addWidget(self.red_plot_widget)

        self.ir_plot_widget = LivePlotWidget(title="IR Light @ 144Hz")
        self.ir_plot_curve = LiveLinePlot()
        self.ir_plot_widget.addItem(self.ir_plot_curve)
        self.ir_data_connector = DataConnector(self.ir_plot_curve, max_points=600, update_rate=144)
        mainLayout.addWidget(self.ir_plot_widget)

    def data_append(self):
        global tick_buffer
        global eog_buffer
        global accelx_buffer
        global accely_buffer
        global accelz_buffer
        global heartir_buffer
        global heartred_buffer
        tick = 0
        initial_tick = 0
        firstRecorded = False
        while(running):
            try:
                data = eog_buffer.popleft()
                self.eog_data_connector.cb_append_data_point(data[0], data[1])
                data = accelx_buffer.popleft()
                self.ax_data_connector.cb_append_data_point(data[0], data[1])
                data = accely_buffer.popleft()
                self.ay_data_connector.cb_append_data_point(data[0], data[1])
                data = accelz_buffer.popleft()
                self.az_data_connector.cb_append_data_point(data[0], data[1])
                data = heartred_buffer.popleft()
                self.ir_data_connector.cb_append_data_point(data[0], data[1])
                data = heartir_buffer.popleft()
                self.red_data_connector.cb_append_data_point(data[0], data[1])

                
            except Exception as e:
                #print(e)
                sleep(0.01)
                pass
            sleep(0.01)

async def run_async_process():
    ble_handler = BLEHandler()
    while(running):
        try:
            await ble_handler.init_connection()
            await ble_handler.start_recording()
        except:
            print("Disconnected from mask. Reconnecting.")
            

def async_thread_target():
    asyncio.run(run_async_process())

def main():
    app = QtWidgets.QApplication(sys.argv)
    graph = GraphWidget()
    graph.show()
    #graph.resize(640, 480)
    t1 = Thread(target=async_thread_target)
    t2 = Thread(target=graph.data_append)

    t1.start()
    t2.start()
    app.exec()


if __name__ == "__main__":
    main()
