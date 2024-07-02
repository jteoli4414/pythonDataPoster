import collections
import asyncio
from bleak import BleakScanner, BleakClient, BLEDevice
from multiprocessing import Process, Queue
from PySide6 import QtCore, QtGui, QtWidgets
from threading import Thread
import time
import struct

DATA_GROUPS = 7
NUM_BUFFER_TYPES = 7
DATA_LENGTH = DATA_GROUPS * NUM_BUFFER_TYPES

UUID_MANUFACTURER = "00002a29-0000-1000-8000-00805f9b34fb"
UUID_MODEL_NUMBER = "00002a24-0000-1000-8000-00805f9b34fb"
UUID_SERIAL_NUMBER = "00002a25-0000-1000-8000-00805f9b34fb"
UUID_FIRMWARE_REVISION ="00002a26-0000-1000-8000-00805f9b34fb"

UUID_BATTERY_LEVEL = "00002a19-0000-1000-8000-00805f9b34fb"

UUID_MASK_READ = "00000011-0000-1000-8000-00805f9b34fb"
UUID_MASK_CMD = "00000021-0000-1000-8000-00805f9b34fb"

# Sleep Executive Command Constants
CMD_START_BURST_READ = bytearray(b'\x00')
CMD_PEAK_BUFFER = bytearray(b'\x01')
CMD_LED_CONTROL = bytearray(b'\x02')
CMD_TOGGLE_SAMPLING = bytearray(b'\x03')

UINT32_MAX = 4294967296
CORRECT_OFFSET_AX = 900
CORRECT_OFFSET_AY = 80
CORRECT_OFFSET_AZ = -18100

# Mask Data Buffers
BUFFER_SYNC = bytearray(b'\x00')
BUFFER_SIZE = 128

class DreamBandBuffer():
    def __init__(self, bufferName):
        self.bufferName = bufferName
        self.queue = collections.deque(maxlen=BUFFER_SIZE, iterable=(0,0))
# Will manage connection to dreamband
# Object functions to control dreamband operations

# and signal data has changed
# Handles SleepMask connection states
class DreamBandHandler(QtCore.QThread):

    def __init__(self, dataQueue:Queue, eventQueue:Queue, controlQueue:Queue):
        super().__init__()
        self.initalTick = 0
        self.initalTime = 0
        self.sleepMaskDevice = None # Handler for BLE
        self.connectionContext = None # Connection context
        self.is_connected = False # Flag for connection state
        self.is_recording = False # Flag for recording state
        self.isListening = False
        self.recordingThread = False
        self.isTimeInitialized = False # Flag for initializing time
        self.dataQueue = dataQueue # Data sending queue for other processes
        self.eventQueue = eventQueue # Event sending queue for stat collection and event collection and logging
        self.controlQueue = controlQueue

        # SleepMask MetaData
        self.model_number = ""
        self.manufacturer = ""
        self.firmware_version = ""
        self.serial_number = ""
        self.battery_level = ""

    async def init_connection(self):

        if(self.is_connected == True):
            self.eventQueue.put(["BleInvalidRequest", "Mask is already connected."])
            return
        devices = await BleakScanner.discover()
        for d in devices:
            if(d.name == "Hypnogogia Mask"):
                self.sleepMaskDevice = d
                self.connectionContext = BleakClient(self.sleepMaskDevice.address)
                try:
                    await self.connectionContext.connect()
                    self.eventQueue.put(["BleConnectionEvent",f"Mask paired."])
                    self.is_connected = True
                    await self.read_mask_info()
                except Exception as e:
                    self.eventQueue.put(["BleConnectionError",f"Could not pair. {str(e)}"])
                    break
                break

    async def del_connection(self):
        if(not self.is_connected):
            self.eventQueue.put(["BleInvalidRequest", f"Mask already disconnected."])
            return
        try:
            await self.connectionContext.disconnect()
            self.eventQueue.put(["BleDisconnectedEvent", f"Band was disconnected. {str(e)}"])
            self.is_connected = False
        except Exception as e:
            self.eventQueue.put(["BleInvalidRequest", f"Could not unpair. {str(e)}"])

    async def read_mask_info(self):
        if(not self.is_connected):
            self.eventQueue.put(["BleInvalidRequest", "Cannot read mask info, mask is not connected."])
            return
        
        self.model_number = await self.connectionContext.read_gatt_char(UUID_MODEL_NUMBER)
        self.eventQueue.put(["BleRead","Read GATT, Read band model number."])
        self.manufacturer = await self.connectionContext.read_gatt_char(UUID_MANUFACTURER)
        self.eventQueue.put(["BleRead","Read GATT, Read band manufacturer."])
        self.firmware_version = await self.connectionContext.read_gatt_char(UUID_FIRMWARE_REVISION)
        self.eventQueue.put(["BleRead","Read GATT, Read band firmware revision."])
        self.serial_number = await self.connectionContext.read_gatt_char(UUID_SERIAL_NUMBER)
        self.eventQueue.put(["BleRead","Read GATT, Read band serial number."])
        self.battery_level = await self.connectionContext.read_gatt_char(UUID_BATTERY_LEVEL)
        self.eventQueue.put(["BleRead","Read GATT, Read band current battery level."])

    async def toggle_sampling(self):
        await self.connectionContext.write_gatt_char(UUID_MASK_CMD, CMD_TOGGLE_SAMPLING, response=False)
        self.eventQueue.put(["BleWrite","Write GATT, Toggle sampling command."])
        return_code = int.from_bytes((await self.connectionContext.read_gatt_char(UUID_MASK_CMD)), "little", signed="False")
        self.eventQueue.put(["BleRead","Read GATT, Read the GATT return code."])
        if(return_code != 0):
            self.eventQueue.put(["BleErrorCode",f"Error Toggling Sampling: {str(return_code)}"])

    async def read_data_buffer(self, buf_sel):
        await self.connectionContext.write_gatt_char(UUID_MASK_CMD, (CMD_START_BURST_READ + buf_sel), response=False)
        self.eventQueue.put(["BleWrite","Write GATT, Initiate a mask buffer read."])
        return_code = int.from_bytes((await self.connectionContext.read_gatt_char(UUID_MASK_CMD)), "little", signed="False")
        self.eventQueue.put(["BleRead","Read GATT, Read the GATT return code."])
        if(return_code != 0):
            self.eventQueue.put(["BleErrorCode",f"Error Starting Burst Read: {str(return_code)}"])
            return
        buffersize = int.from_bytes((await self.connectionContext.read_gatt_char(UUID_MASK_READ)), "little", signed="False")
        self.eventQueue.put(["BleRead",f"Read GATT, Read buffer size: {str(buffersize)}."])
        for x in range(0,buffersize):
            data = await self.connectionContext.read_gatt_char(UUID_MASK_READ)
            self.eventQueue.put(["BleRead",f"Read GATT, Read a buffer sample {str(x)}."])
            # Unpack into unsigned integers
            data_unpacked = struct.unpack((str(DATA_LENGTH)+'I'), data)
            self.data_into_buffer(data_unpacked)

    def tick_time_correct(self, tick):
        ticks_passed = tick - self.initalTick
        seconds = ticks_passed / 1000000
        return(self.initalTime + seconds)

    def data_into_buffer(self, data):
        # Group integers into buffer types 
        for group in range(0, DATA_GROUPS):
            tick = data[0 + (NUM_BUFFER_TYPES * group)]
            if(self.isTimeInitialized == False):
                self.initalTick = tick
                self.initalTime = time.time()
                self.isTimeInitialized = True
            correctedTime = self.tick_time_correct(tick)  

            self.dataQueue.put([data[1 + (NUM_BUFFER_TYPES * group)], correctedTime, "EOG"])
            correctedAx = data[2 + (NUM_BUFFER_TYPES * group)] - (UINT32_MAX/2) + CORRECT_OFFSET_AX
            correctedAy = data[3 + (NUM_BUFFER_TYPES * group)] - (UINT32_MAX/2) + CORRECT_OFFSET_AY
            correctedAz = data[4 + (NUM_BUFFER_TYPES * group)] - (UINT32_MAX/2) + CORRECT_OFFSET_AZ
            self.dataQueue.put([correctedAx, correctedTime, "Accel X"])
            self.dataQueue.put([correctedAy, correctedTime, "Accel Y"])
            self.dataQueue.put([correctedAz, correctedTime, "Accel Z"])
            self.dataQueue.put([data[5 + (NUM_BUFFER_TYPES * group)], correctedTime, "Red Light"])
            self.dataQueue.put([data[6 + (NUM_BUFFER_TYPES * group)], correctedTime, "IR Light"])

    async def start_recording(self):
        self.isTimeInitialized = False
        self.initalTick = 0
        self.initalTime = 0
        
        if(not self.is_connected):
            self.eventQueue.put(["BleInvalidRequest","Cannot Record, Mask is not connected."])

        await self.toggle_sampling()
        self.eventQueue.put(["BleToggleSamplingEvent","Mask was toggled to start sampling data."])
        self.is_recording = True

        while (self.is_recording):
            await self.read_data_buffer(BUFFER_SYNC)
        
        await self.toggle_sampling()
        self.eventQueue.put(["BleToggleSamplingEvent","Mask was toggled to stop sampling data."])

        self.isTimeInitialized = False
        self.initalTick = 0
        self.initalTime = 0

    async def stop_recording(self):
        if(not self.is_connected):
            self.eventQueue.put(["BleInvalidRequest","Cannot Stop Recoding, Mask is not connected"])
        self.is_recording = False

    def _init_connection(self):
        asyncio.run(self.init_connection())

    def _del_connection(self):
        asyncio.run(self.del_connection())

    def _start_recording(self):
        asyncio.run(self.start_recording())

    def _stop_recording(self):
        asyncio.run(self.stop_recording())

    def run(self):
        self.isListening = True
        self.listener()

    def die(self):
        self.isListening = False

    def listener(self):
        self.eventQueue.put(["BleControlThreadStart", f"The BLE control thread has started."])
        while(self.isListening):
            if(self.controlQueue.empty() == False):
                command = self.controlQueue.get()[0]
                if(command == "BleControlStopRecording"):
                    self.recordingThread = False
                    self._stop_recording()
                elif(command == "BleControlStartRecording"):
                    # Create a seperate Thread (Not QThread since not a GUI Processes)
                    if(not self.recordingThread):
                        recordingProcess = Thread(target=self._start_recording)
                        recordingProcess.start()
                        self.recordingThread = True
                elif(command == "BleControlConnect"):
                    self._init_connection()
                elif(command == "BleControlDisconnect"):
                    self._del_connection()
            time.sleep(0.5)
