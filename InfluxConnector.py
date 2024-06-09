from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from multiprocessing import Process, Queue
import datetime
import time

INFLUXDB_TOKEN="K9rGmJj1SDnItm98_HobnBIZGkXU__2LVj44w2S_9JQr4B-DtD_xe0QJXt-nUlU8CC1XRgDNDhgLyov_Dlf-9g=="
INFLUX_ORG = "AlpineDreamwareLLC"
INFLUX_URL = "http://192.168.1.13:8086"
INFLUX_MEASUREMENT_TYPE = "Dreamband_v1"
INFLUX_BUCKET = "Hypnagogia_v1"


class InfluxConnector():
    def __init__(self, dbQueue:Queue):
        self.write_client = InfluxDBClient(url=INFLUX_URL, token=INFLUXDB_TOKEN)
        self.isListening = True
        self.dbQueue = dbQueue
        self.sendBatch = []

    def createInfluxPoint(self, data, time, measurement):
        point = Point(INFLUX_MEASUREMENT_TYPE).field(measurement,data)
        local_dt = datetime.datetime.fromtimestamp(time)
        local_dt_est = local_dt + datetime.timedelta(hours=4)
        iso_format = local_dt_est.isoformat()
        point.time(iso_format, WritePrecision.NS)
        return point

    def postDataInflux(self, data, time, measurement):
        point = Point(INFLUX_MEASUREMENT_TYPE).field(measurement,data)
        local_dt = datetime.datetime.fromtimestamp(time)
        local_dt_est = local_dt + datetime.timedelta(hours=4)
        iso_format = local_dt_est.isoformat()
        point.time(iso_format, WritePrecision.NS)

        write_api = self.write_client.write_api(write_options=SYNCHRONOUS)
        write_api.write(INFLUX_BUCKET, INFLUX_ORG, point)
    
    def postBatchDataInflux(self):
        write_api = self.write_client.write_api(write_options=SYNCHRONOUS)
        write_api.write(INFLUX_BUCKET, INFLUX_ORG, record=self.sendBatch)
        self.sendBatch = []

    def start_listening(self):
        self.isListening = True
        self.listen()

    def listen(self):
        while(self.isListening):
            if(self.dbQueue.empty() == False):
                to_post = self.dbQueue.get()
                createPoint = self.createInfluxPoint(to_post[0], to_post[1], to_post[2])
                self.sendBatch.append(createPoint)
            if(len(self.sendBatch) == 1000):
                self.postBatchDataInflux()

    def stop_listening(self):
        self.isListening = False