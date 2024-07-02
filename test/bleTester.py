import asyncio
from bleak import BleakScanner, BleakClient, BLEDevice
import time
import ctypes
import struct

sleepMask = None
UUID_MANUFACTURER = "00002a29-0000-1000-8000-00805f9b34fb"
UUID_MODEL_NUMBER = "00002a24-0000-1000-8000-00805f9b34fb"
UUID_SERIAL_NUMBER = "00002a25-0000-1000-8000-00805f9b34fb"
UUID_FIRMWARE_REVISION ="00002a26-0000-1000-8000-00805f9b34fb"

UUID_BATTERY_LEVEL = "00002a19-0000-1000-8000-00805f9b34fb"

UUID_MASK_READ = "00000011-0000-1000-8000-00805f9b34fb"
UUID_MASK_CMD = "00000021-0000-1000-8000-00805f9b34fb"


# Sleep Executive Command
CMD_START_BURST_READ = bytearray(b'\x00')
CMD_PEAK_BUFFER = bytearray(b'\x01')
CMD_LED_CONTROL = bytearray(b'\x02')
CMD_TOGGLE_SAMPLING = bytearray(b'\x03')

# Mask Data Buffers
# EOG
BUFFER_EOGH = bytearray(b'\x00')
BUFFER_SYNC = bytearray(b'\x00')
BUFFER_EOGV = bytearray(b'\x01')
# ACCEL
BUFFER_AX = bytearray(b'\x02')
BUFFER_AY = bytearray(b'\x03')
BUFFER_AZ = bytearray(b'\x04')
# HBM
BUFFER_RED  = bytearray(b'\x05')
BUFFER_IR = bytearray(b'\x06')
# FNIRS
BUFFER_FNIRS_RED_6  = bytearray(b'\x07')
BUFFER_FNIRS_RED_25  = bytearray(b'\x08')
BUFFER_FNIRS_IR_6 = bytearray(b'\x09')
BUFFER_FNIRS_IR_25 = bytearray(b'\x0a')
BUFFER_FNIRS_AMB_6 = bytearray(b'\x0b')
BUFFER_FNIRS_AMB_25 = bytearray(b'\x0c')

"""
Read buffer from server.
"""
async def readBufferRaw(buf_type, client, printing=True):
    await client.write_gatt_char(UUID_MASK_CMD, (CMD_START_BURST_READ + buf_type), response=False)
    return_code = await client.read_gatt_char(UUID_MASK_CMD)
    if(printing):
        print(f"CMD_START_BURST_READ: {return_code}")
    buffersize = int.from_bytes((await client.read_gatt_char(UUID_MASK_READ)), "little", signed="False")
    if(printing):
        print(f"Current Queue Size: {buffersize}")
    ret = []
    for x in range(0,buffersize):
        buffer = await client.read_gatt_char(UUID_MASK_READ)
        ret.append(buffer)
        if(printing):
            print(f"Buffer {x}: {buffer}")
    return buffersize, ret

async def readBufferDecom(buf_type, client, printing=True):
    await client.write_gatt_char(UUID_MASK_CMD, (CMD_START_BURST_READ + buf_type), response=False)
    return_code = await client.read_gatt_char(UUID_MASK_CMD)
    if(printing):
        print(f"CMD_START_BURST_READ: {return_code}")
    buffersize = int.from_bytes((await client.read_gatt_char(UUID_MASK_READ)), "little", signed="False")
    if(printing):
        print(f"Current Queue Size: {buffersize}")
    ret = []
    for x in range(0,buffersize):
        buffer = await client.read_gatt_char(UUID_MASK_READ)
        if(printing):
            print(f"Buffer {x}: {buffer}")
            print(f"Buffer Length {x}: {str(len(buffer))}")
        ret.append(struct.unpack('55I', buffer))
    print(ret)
    return buffersize, ret # Return how many structs there are and the structs

async def readAllBuffersDecom(client):
    await readBufferDecom(BUFFER_SYNC, client)

"""
Read all buffers from server.
"""
async def readAllBuffersRaw(client):
    await readBufferRaw(BUFFER_SYNC, client)
"""
Check buffer size from server.
"""
async def checkBufferSize(buf_type, client):
    await client.write_gatt_char(UUID_MASK_CMD, (CMD_START_BURST_READ + buf_type), response=False)
    return_code = await client.read_gatt_char(UUID_MASK_CMD)
    print(f"CMD_START_BURST_READ: {return_code}")
    buffersize = int.from_bytes((await client.read_gatt_char(UUID_MASK_READ)), "little", signed="False")
    print(f"Current Queue Size: {buffersize}")

"""
Check all buffer size from server.
"""
async def checkAllBufferSize(client):
    await checkBufferSize(BUFFER_SYNC, client)

async def toggleSampling(client):
    await client.write_gatt_char(UUID_MASK_CMD, CMD_TOGGLE_SAMPLING, response=False)
    return_code = await client.read_gatt_char(UUID_MASK_CMD)
    print(f"CMD_TOGGLE_SAMPLING: {return_code}")

"""
Main Test function
"""
async def test0():
    devices = await BleakScanner.discover()
    for d in devices:
        if(d.name == "Hypnogogia Mask"):
            print("Found Sleep Mask!")
            sleepMask = d
    
    print("Trying to connect...")
    async with BleakClient(sleepMask.address) as client:
        print("Connected!")
        print("          ")

        print("Pairing!")
        print("          ")

        try:
            await client.pair()
        except:
            print("Could not pair. Exiting... ")
            return
        
        model_number = await client.read_gatt_char(UUID_MODEL_NUMBER)
        manufacturer = await client.read_gatt_char(UUID_MANUFACTURER)
        firmware_version = await client.read_gatt_char(UUID_FIRMWARE_REVISION)
        serial_number = await client.read_gatt_char(UUID_SERIAL_NUMBER)
        battery_level = await client.read_gatt_char(UUID_BATTERY_LEVEL)

        print("=====DEVICE INFO=====")
        print("Model Number: {0}".format("".join(map(chr, model_number))))
        print("Manufacturer: {0}".format("".join(map(chr, manufacturer))))
        print("Firmware Version: {0}".format("".join(map(chr, firmware_version))))
        print("Serial Number: {0}".format("".join(map(chr, serial_number))))
        print("Current Battery Level: {0}".format("".join(map(chr, battery_level))))
        print("=====================")
        print(" ")


        print("=====Start Testing Scenerio 0=====")
        print(" ")
        
        #========================================================================
        # Test 1 Start Recording/Stop Recording
        #========================================================================
        print("Test 1 Start Recording, Stop Recording")

        await toggleSampling(client)

        await asyncio.sleep(10)

        await toggleSampling(client)
        
        await asyncio.sleep(1)
        #========================================================================
        # Test 2 Start Recording, Check Buffer Size, Stop Recording
        #========================================================================
        print(" ")
        print("Test 2 Start, Check Buffer Size, Stop Recording")

        # Turn on sampling
        await toggleSampling(client)

        await asyncio.sleep(1)

        # Check all buffer sizes
        await checkAllBufferSize(client)

        # Turn off sampling
        await toggleSampling(client)

        await asyncio.sleep(1)
        
        #========================================================================
        # Test 3 Start Recording, Read Buffers, Stop Recording
        #========================================================================
        print(" ")
        print("Test 3 Start Recording, Read Buffers, Stop Recording")

        # Turn on sampling
        await toggleSampling(client)

        await asyncio.sleep(1)

        # Read All Buffers
        await readAllBuffersRaw(client)
            
        # Turn off sampling
        await toggleSampling(client)

        await asyncio.sleep(1)

        #========================================================================
        # Test 4 Start Recording, Read Buffers Continually, Stop Recording
        #========================================================================
        print(" ")
        print("Test 4 Start Recording, Read Buffers Continually (5x), Stop Recording")

        # Turn on sampling
        await toggleSampling(client)

        await asyncio.sleep(1)
        # Read All Buffers
        await readAllBuffersRaw(client)
        await asyncio.sleep(1)
        await readAllBuffersRaw(client)
        await asyncio.sleep(1)
        await readAllBuffersRaw(client)
        await asyncio.sleep(1)
        await readAllBuffersRaw(client)
        await asyncio.sleep(1)
        await readAllBuffersRaw(client)
        await asyncio.sleep(1)
            
        # Turn off sampling
        await toggleSampling(client)

        print(" ")
        print("=====Testing Scenerio 0 Done=====")
        print(" ")
        await client.unpair()
        print("Client Unparied")

async def test1():
    devices = await BleakScanner.discover()
    for d in devices:
        if(d.name == "Hypnogogia Mask"):
            print("Found Sleep Mask!")
            sleepMask = d
    
    print("Trying to connect...")
    async with BleakClient(sleepMask.address) as client:
        print("Connected!")
        print("          ")

        print("Pairing!")
        print("          ")

        try:
            await client.pair()
        except:
            print("Could not pair. Exiting... ")
            return
        
        model_number = await client.read_gatt_char(UUID_MODEL_NUMBER)
        manufacturer = await client.read_gatt_char(UUID_MANUFACTURER)
        firmware_version = await client.read_gatt_char(UUID_FIRMWARE_REVISION)
        serial_number = await client.read_gatt_char(UUID_SERIAL_NUMBER)
        battery_level = await client.read_gatt_char(UUID_BATTERY_LEVEL)

        print("=====DEVICE INFO=====")
        print("Model Number: {0}".format("".join(map(chr, model_number))))
        print("Manufacturer: {0}".format("".join(map(chr, manufacturer))))
        print("Firmware Version: {0}".format("".join(map(chr, firmware_version))))
        print("Serial Number: {0}".format("".join(map(chr, serial_number))))
        print("Current Battery Level: {0}".format("".join(map(chr, battery_level))))
        print("=====================")
        print(" ")

        print("=====Start Testing Scenerio 1=====")
        print(" ")


        #========================================================================
        # Test 1 Read Buffers Continually (20x) 1 Second Bursts, Stop Recording
        #========================================================================
        print(" ")
        print("Test 1 Read Buffers Continually (20x) 1 Second Bursts, Stop Recording")

        # Turn on sampling
        await toggleSampling(client)

        for x in range(0,20):
            await asyncio.sleep(1)
            # Read All Buffers
            await readAllBuffersRaw(client)
            # Turn off sampling
        await toggleSampling(client)

        await asyncio.sleep(1)

        #========================================================================
        # Test 2 Start Recording, Read Buffers Continually no wait, Stop Recording
        #========================================================================
        print(" ")
        print("Test 2 Read Buffers Continually (100x) 1 Second Bursts, Stop Recording")

        # Turn on sampling
        await toggleSampling(client)

        for x in range(0,100):
            # Read All Buffers
            await readAllBuffersRaw(client)
            # Turn off sampling
        await toggleSampling(client)

        await asyncio.sleep(1)


        print(" ")
        print("=====Testing Scenerio 1 Done=====")
        print(" ")
        await client.unpair()
        print("Client Unparied")

async def test2():
    devices = await BleakScanner.discover()
    for d in devices:
        if(d.name == "Hypnogogia Mask"):
            print("Found Sleep Mask!")
            sleepMask = d
    
    print("Trying to connect...")
    async with BleakClient(sleepMask.address) as client:
        print("Connected!")
        print("          ")

        print("Pairing!")
        print("          ")

        try:
            await client.pair()
        except:
            print("Could not pair. Exiting... ")
            return
        
        model_number = await client.read_gatt_char(UUID_MODEL_NUMBER)
        manufacturer = await client.read_gatt_char(UUID_MANUFACTURER)
        firmware_version = await client.read_gatt_char(UUID_FIRMWARE_REVISION)
        serial_number = await client.read_gatt_char(UUID_SERIAL_NUMBER)
        battery_level = await client.read_gatt_char(UUID_BATTERY_LEVEL)

        print("=====DEVICE INFO=====")
        print("Model Number: {0}".format("".join(map(chr, model_number))))
        print("Manufacturer: {0}".format("".join(map(chr, manufacturer))))
        print("Firmware Version: {0}".format("".join(map(chr, firmware_version))))
        print("Serial Number: {0}".format("".join(map(chr, serial_number))))
        print("Current Battery Level: {0}".format("".join(map(chr, battery_level))))
        print("=====================")
        print(" ")

        print("=====Start Testing Scenerio 2=====")
        print(" ")


        #========================================================================
        # Test 1 Read Buffers Continually (20x) 1 Second Bursts, Stop Recording
        #========================================================================
        print(" ")
        print("Test 1 Read Buffers Continually (20x) and decomutate data, Stop Recording")

        # Turn on sampling
        await toggleSampling(client)

        for x in range(0,1000):
            # Read All Buffers
            await readAllBuffersDecom(client)
            # Turn off sampling
        await toggleSampling(client)

        await asyncio.sleep(1)


        print(" ")
        print("=====Testing Scenerio 2 Done=====")
        print(" ")
        await client.unpair()
        print("Client Unparied")

# Toggling and recording
#asyncio.run(test0())
# Recording continually
#asyncio.run(test1())
# Recording continually while decommutating bytes
asyncio.run(test2())
