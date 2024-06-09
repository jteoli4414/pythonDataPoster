import collections
import asyncio
from bleak import BleakScanner, BleakClient, BLEDevice
from multiprocessing import Process, Queue
import time
import struct
import sys

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
class DreamBandHandler():

    def __init__(self, dataQueue:Queue):
        super().__init__()
        self.initalTick = 0
        self.initalTime = 0
        self.sleepMaskDevice = None # Handler for BLE
        self.connectionContext = None # Connection context
        self.is_connected = False # Flag for connection state
        self.is_recording = False # Flag for recording state
        self.isTimeInitialized = False # Flag for initializing time
        self.dataQueue = dataQueue # Data sending queue for other processes

        # SleepMask MetaData
        self.model_number = ""
        self.manufacturer = ""
        self.firmware_version = ""
        self.serial_number = ""
        self.battery_level = ""

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

    async def continual_record(self):
        while(True):
            try:
                await self.init_connection()
                await self.start_recording()
            except:
                self.isTimeInitialized = False
                self.initalTick = 0
                self.initalTime = 0
                print("Disconnected from mask. Reconnecting.")

    async def run_async_process(self):            
        await self.continual_record()

    def async_thread_target(self):
        asyncio.run(self.run_async_process())
