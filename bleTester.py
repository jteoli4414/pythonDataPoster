import asyncio
from bleak import BleakScanner, BleakClient, BLEDevice
import time

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
async def readBuffer(buf_type, client):
    await client.write_gatt_char(UUID_MASK_CMD, (CMD_START_BURST_READ + buf_type), response=False)
    return_code = await client.read_gatt_char(UUID_MASK_CMD)
    print(f"CMD_START_BURST_READ: {return_code}")
    buffersize = int.from_bytes((await client.read_gatt_char(UUID_MASK_READ)), "little", signed="False")
    print(f"Current Buffer Size: {buffersize}")
    for x in range(0,buffersize):
        buffer = await client.read_gatt_char(UUID_MASK_READ)
        print(f"Buffer {x}: {buffer}")

"""
Read all buffers from server.
"""
async def readAllBuffers(client):
    await readBuffer(BUFFER_EOGH, client)
    await readBuffer(BUFFER_EOGV, client)
    await readBuffer(BUFFER_FNIRS_RED_6, client)
    await readBuffer(BUFFER_FNIRS_RED_25, client)
    await readBuffer(BUFFER_FNIRS_IR_6, client)
    await readBuffer(BUFFER_FNIRS_IR_25, client)
    # Read ACCEL
    await readBuffer(BUFFER_AX, client)
    await readBuffer(BUFFER_AY, client)
    await readBuffer(BUFFER_AZ, client)
    # Read HBM
    await readBuffer(BUFFER_RED, client)
    await readBuffer(BUFFER_IR, client)
    # Read FNIRS
    await readBuffer(BUFFER_FNIRS_AMB_6, client)
    await readBuffer(BUFFER_FNIRS_AMB_25, client)
"""
Check buffer size from server.
"""
async def checkBufferSize(buf_type, client):
    await client.write_gatt_char(UUID_MASK_CMD, (CMD_START_BURST_READ + buf_type), response=False)
    return_code = await client.read_gatt_char(UUID_MASK_CMD)
    print(f"CMD_START_BURST_READ: {return_code}")
    buffersize = int.from_bytes((await client.read_gatt_char(UUID_MASK_READ)), "little", signed="False")
    print(f"Current Buffer Size: {buffersize}")

"""
Check all buffer size from server.
"""
async def checkAllBufferSize(client):
    await checkBufferSize(BUFFER_EOGH, client)
    await checkBufferSize(BUFFER_EOGV, client)
    # Read ACCEL
    await checkBufferSize(BUFFER_AX, client)
    await checkBufferSize(BUFFER_AY, client)
    await checkBufferSize(BUFFER_AZ, client)
    # Read HBM
    await checkBufferSize(BUFFER_RED, client)
    await checkBufferSize(BUFFER_IR, client)
    # Read FNIRS
    await checkBufferSize(BUFFER_FNIRS_RED_6, client)
    await checkBufferSize(BUFFER_FNIRS_RED_25, client)
    await checkBufferSize(BUFFER_FNIRS_IR_6, client)
    await checkBufferSize(BUFFER_FNIRS_IR_25, client)
    await checkBufferSize(BUFFER_FNIRS_AMB_6, client)
    await checkBufferSize(BUFFER_FNIRS_AMB_25, client)

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


        print("=====Start Testing=====")
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

        await asyncio.sleep(5)

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

        await asyncio.sleep(5)

        # Read All Buffers
        await readAllBuffers(client)
            
        # Turn off sampling
        await toggleSampling(client)

        print(" ")
        print("=====Testing Done=====")
        print(" ")
        await client.unpair()
        print("Client Unparied")

asyncio.run(test0())
