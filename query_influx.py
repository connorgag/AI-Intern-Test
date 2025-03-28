from influxdb_client import InfluxDBClient
from dotenv import load_dotenv
import os

load_dotenv()

# Set up credentials
INFLUX_URL = "http://localhost:8086"  # Change if needed
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_ORG = "none"
INFLUX_BUCKET = "bucket"

# Initialize client
client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
query_api = client.query_api()

# Define Flux query
query = f'''
from(bucket: "{INFLUX_BUCKET}")
  |> range(start: -1h)
  |> filter(fn: (r) => r["_measurement"] == "my_measurement")
  |> filter(fn: (r) => r["_field"] == "value")
  |> yield(name: "result")
'''

# Execute query
tables = query_api.query(query)
for table in tables:
    for record in table.records:
        print(f"Time: {record.get_time()}, Value: {record.get_value()}")
