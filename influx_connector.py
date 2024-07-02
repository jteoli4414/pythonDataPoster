from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS, ASYNCHRONOUS
from multiprocessing import Queue
from PySide6 import QtCore, QtGui, QtWidgets
from threading import Thread
import datetime
import time

INFLUXDB_TOKEN="94pvEtGM0AxCpl4Tz8Wqu3OqHQXGu3d1d4s3J2-Pp_prfofNNPfOEA1ocxBlkEUn9XyFERjGPjf9EEAn5Ct1ZQ=="
INFLUX_ORG = "AlpineDreamwareLLC"
INFLUX_URL = "http://192.168.1.13:8086"
INFLUX_MEASUREMENT_TYPE = "Dreamband_v1"
INFLUX_BUCKET = "Hypnagogia_v1"
BATCH_SIZE = 1000


"""
Event List:
InfluxPostDataEvent - Data was posted to the influx time series database
InfluxControlStartPosting -


Command List:


"""

class InfluxConnector(QtCore.QThread):
    def __init__(self, dataQueue:Queue, eventQueue:Queue, controlQueue:Queue):
        super().__init__()
        self.write_client = InfluxDBClient(url=INFLUX_URL, token=INFLUXDB_TOKEN, debug=False)
        self.isListening = True
        self.postingThread = False
        self.dataQueue = dataQueue
        self.eventQueue = eventQueue
        self.controlQueue = controlQueue
        self.sendBatch = []

    def createInfluxPoint(self, data, time, measurement):
        point = Point(INFLUX_MEASUREMENT_TYPE).field(measurement,data)
        local_dt = datetime.datetime.fromtimestamp(time)
        local_dt_est = local_dt + datetime.timedelta(hours=4)
        iso_format = local_dt_est.isoformat()
        point.time(iso_format, WritePrecision.NS)
        return point
    
    def postBatchDataInflux(self):
        self.write_api = self.write_client.write_api(write_options=SYNCHRONOUS)
        result = self.write_api.write(INFLUX_BUCKET, INFLUX_ORG, record=self.sendBatch)
        self.eventQueue.put(["InfluxPostDataEvent", f"The influx connector posted data to DB."])
        self.sendBatch = []

    def start_posting(self):
        self.isPosting = True
        self.eventQueue.put(["InfluxControlStartPosting", f"The influx connector started listening for db requests."])
        while(self.isPosting):
            if(self.dataQueue.empty() == False):
                to_post = self.dataQueue.get()
                createPoint = self.createInfluxPoint(to_post[0], to_post[1], to_post[2])
                self.sendBatch.append(createPoint)
            if(len(self.sendBatch) >= BATCH_SIZE):
                self.postBatchDataInflux()
        self.eventQueue.put(["InfluxControlStopPosting", f"The influx connector stopped listening for db requests."])

    def stop_posting(self):
        self.isPosting = False

    def run(self):
        self.isListening = True
        self.listener()
    
    def die(self):
        self.isListening = False

    def listener(self):
        self.eventQueue.put(["InfluxControlThreadStart", f"The influx connector control thread has started."])
        while(self.isListening):
            if(self.controlQueue.empty() == False):
                command = self.controlQueue.get()[0]
                if(command == "InfluxControlStopPosting"):
                    self.stop_posting()
                    self.postingThread = False
                elif(command == "InfluxControlStartPosting"):
                    # Create a seperate process
                    if(not self.postingThread):
                        postingProcess = Thread(target=self.start_posting)
                        self.postingThread = True
                        postingProcess.start()
                    

            time.sleep(0.5)