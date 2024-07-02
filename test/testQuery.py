import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS
import matplotlib.pyplot as plt

INFLUXDB_TOKEN="K9rGmJj1SDnItm98_HobnBIZGkXU__2LVj44w2S_9JQr4B-DtD_xe0QJXt-nUlU8CC1XRgDNDhgLyov_Dlf-9g=="
INFLUX_ORG = "AlpineDreamwareLLC"
INFLUX_URL = "http://192.168.1.13:8086"
INFLUX_MEASUREMENT_TYPE = "Dreamband_v1"
INFLUX_BUCKET = "Hypnagogia_v1"

bucket = INFLUX_BUCKET
org = INFLUX_ORG
token = INFLUXDB_TOKEN
url = INFLUX_URL  # Adjust this to your InfluxDB instance URL

client = influxdb_client.InfluxDBClient(url=url, token=token, org=org)

query_api = client.query_api()

query = '''
from(bucket:"{}")
|> range(start: -30s)
|> filter(fn:(r) => r._measurement == "Dreamband_v1")
|> filter(fn:(r) => r._field == "Accel X")
'''.format(bucket)

result = query_api.query(org=org, query=query)

timestamps = []  # Extracted timestamps
measurments = []  # Extracted temperatures

for table in result:
    for record in table.records:
        timestamps.append(record.get_time())
        measurments.append(record.get_value())


plt.plot(timestamps, measurments)
plt.xlabel('Timestamp')
plt.ylabel('A Sensor')
plt.title('A Sensor over recent 30s Epoch')
plt.show()