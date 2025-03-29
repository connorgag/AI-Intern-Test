import random
from datetime import datetime, timedelta
import math
import json
import os
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from dotenv import load_dotenv


class SensorDataGenerator:
    def __init__(self, start_time, duration_days=7, interval_minutes=5):
        """
        Initialize sensor data generator for a dormitory building
        
        :param start_time: Starting datetime for data generation
        :param duration_days: Number of days to generate data for
        :param interval_minutes: Interval between data points
        """
        self.start_time = start_time
        self.duration_days = duration_days
        self.interval_minutes = interval_minutes
        self.total_points = (duration_days * 24 * 60) // interval_minutes
        
        # Define room and sensor configuration
        self.rooms = {
            'dorm1': {'type': 'dorm', 'ac_unit': 'ac_unit1', 'temp_sensor': 'temp_sensor1', 'occupancy_sensor': 'occ_sensor1'},
            'dorm2': {'type': 'dorm', 'ac_unit': 'ac_unit1', 'temp_sensor': 'temp_sensor2', 'occupancy_sensor': 'occ_sensor2'},
            'dorm3': {'type': 'dorm', 'ac_unit': 'ac_unit1', 'temp_sensor': 'temp_sensor3', 'occupancy_sensor': 'occ_sensor3'},
            'dorm4': {'type': 'dorm', 'ac_unit': 'ac_unit2', 'temp_sensor': 'temp_sensor4', 'occupancy_sensor': 'occ_sensor4'},
            'dorm5': {'type': 'dorm', 'ac_unit': 'ac_unit2', 'temp_sensor': 'temp_sensor5', 'occupancy_sensor': 'occ_sensor5'},
            'dorm6': {'type': 'dorm', 'ac_unit': 'ac_unit2', 'temp_sensor': 'temp_sensor6', 'occupancy_sensor': 'occ_sensor6'},
            'mech1': {'type': 'mechanical', 'ac_unit': 'ac_unit1'},
            'mech2': {'type': 'mechanical', 'ac_unit': 'ac_unit2'}
        }

    def temp_curve(self, t, base_temp=22, amplitude=3, sun_factor=0):
        """
        Generate a more realistic temperature curve
        
        :param t: Time (in hours)
        :param base_temp: Base temperature
        :param amplitude: Temperature variation amplitude
        :param sun_factor: Additional warmth for sun-facing rooms
        :return: Temperature value
        """
        # Simulate daily temperature cycle with more natural variation
        temp = base_temp + amplitude * math.sin(2 * math.pi * t / 24 - math.pi/2)
        
        # Add sun exposure effect
        temp += sun_factor
        
        # Add more realistic random noise
        temp += random.gauss(0, 0.5)
        
        return round(temp, 2)

    def generate_occupancy_profiles(self):
        """
        Generate more detailed occupancy profiles with overnight occupancy,
        including explicitly unoccupied periods.
        
        :return: Dictionary of occupancy profiles
        """
        return {
            'dorm1': [
                ((7, 9), 1),     # Morning classes
                ((9, 12), 0),    # Explicitly unoccupied from 9:00 to 12:00
                ((12, 14), 1),   # Lunch break
                ((14, 19), 0),   # Explicitly unoccupied from 14:00 to 19:00
                ((19, 23), 1),   # Evening study/social time
                ((23, 7), 1)     # Night sleep (occupied)
            ],
            'dorm2': [
                ((6, 8), 1),     # Early morning
                ((8, 16), 0),    # Explicitly unoccupied from 8:00 to 16:00
                ((16, 18), 1),   # Late afternoon
                ((18, 21), 0),   # Explicitly unoccupied from 18:00 to 21:00
                ((21, 23), 1),   # Evening
                ((23, 6), 1)     # Night sleep (occupied)
            ],
            'dorm3': [
                ((8, 10), 1),    # Morning
                ((10, 13), 0),   # Explicitly unoccupied from 10:00 to 13:00
                ((13, 15), 1),   # Afternoon
                ((15, 20), 0),   # Explicitly unoccupied from 15:00 to 20:00
                ((20, 22), 1),   # Evening
                ((22, 8), 1)     # Night sleep (occupied)
            ],
            'dorm4': [
                ((7, 9), 1),     # Morning
                ((9, 12), 0),    # Explicitly unoccupied from 9:00 to 12:00
                ((12, 14), 1),   # Midday
                ((14, 18), 0),   # Explicitly unoccupied from 14:00 to 18:00
                ((18, 22), 1),   # Evening
                ((22, 7), 1)     # Night sleep (occupied)
            ],
            'dorm5': [
                ((6, 8), 1),     # Early morning
                ((8, 16), 0),    # Explicitly unoccupied from 8:00 to 16:00
                ((16, 18), 1),   # Late afternoon
                ((18, 21), 0),   # Explicitly unoccupied from 18:00 to 21:00
                ((21, 23), 1),   # Evening
                ((23, 6), 1)     # Night sleep (occupied)
            ],
            'dorm6': [
                ((8, 10), 1),    # Morning
                ((10, 13), 0),   # Explicitly unoccupied from 10:00 to 13:00
                ((13, 15), 1),   # Afternoon
                ((15, 20), 0),   # Explicitly unoccupied from 15:00 to 20:00
                ((20, 22), 1),   # Evening
                ((22, 8), 1)     # Night sleep (occupied)
            ]
        }

    def is_time_in_range(self, hour, time_ranges):
        """
        Check if the hour is within any of the given time ranges
        
        :param hour: Current hour (float)
        :param time_ranges: List of tuples with time ranges
        :return: Binary occupancy value
        """
        for (start, end), value in time_ranges:
            # Handle time ranges that cross midnight
            if start > end:
                if hour >= start or hour < end:
                    return value
            # Normal time range
            else:
                if start <= hour < end:
                    return value
        return 0

    def generate_sensor_data(self):
        """
        Generate comprehensive sensor data for all rooms
        
        :return: Tuple of lists containing occupancy and temperature data
        """
        # Prepare occupancy profiles
        occupancy_profiles = self.generate_occupancy_profiles()
        
        # Prepare data structures
        sensor_data = {
            'occupancy': [],
            'temperature': []
        }
        
        # Define temperature characteristics for different AC zones
        ac_zones = {
            'ac_unit1': {'base_temp': 22, 'sun_factor': 2},   # Warmer side of building
            'ac_unit2': {'base_temp': 20, 'sun_factor': 0}    # Less sun-exposed side
        }
        
        # Generate data points
        for i in range(self.total_points):
            # Calculate current timestamp and time of day
            current_time = self.start_time + timedelta(minutes=i*self.interval_minutes)
            hour = current_time.hour + current_time.minute / 60
            
            # Process each dorm room
            for room_name, room_config in self.rooms.items():
                if room_config['type'] == 'dorm':
                    # Occupancy data
                    occupancy = self.is_time_in_range(
                        hour, 
                        occupancy_profiles[room_name]
                    )
                    
                    # Temperature data based on AC unit
                    ac_unit = room_config['ac_unit']
                    zone_config = ac_zones[ac_unit]
                    temp = self.temp_curve(
                        hour, 
                        base_temp=zone_config['base_temp'],
                        sun_factor=zone_config['sun_factor']
                    )
                    
                    # Store occupancy data
                    sensor_data['occupancy'].append({
                        'time': current_time.isoformat(),
                        'room': room_name,
                        'occupancy_sensor': room_config['occupancy_sensor'],
                        'ac_unit': ac_unit,
                        'value': occupancy
                    })
                    
                    # Store temperature data
                    sensor_data['temperature'].append({
                        'time': current_time.isoformat(),
                        'room': room_name,
                        'temp_sensor': room_config['temp_sensor'],
                        'ac_unit': ac_unit,
                        'value': temp
                    })
        
        return sensor_data

    def save_sensor_data(self, sensor_data, output_dir='sensor_data'):
        """
        Save generated sensor data to JSON files
        
        :param sensor_data: Dictionary of sensor data
        :param output_dir: Directory to save data files
        """
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Save occupancy data
        occupancy_file = os.path.join(output_dir, 'occupancy_data.json')
        with open(occupancy_file, 'w') as f:
            json.dump(sensor_data['occupancy'], f, indent=2)
        
        # Save temperature data
        temperature_file = os.path.join(output_dir, 'temperature_data.json')
        with open(temperature_file, 'w') as f:
            json.dump(sensor_data['temperature'], f, indent=2)
        
        print(f"Sensor data saved to {output_dir}")
        return occupancy_file, temperature_file
    

def delete_existing_data(influx_url, influx_token, influx_org, influx_bucket):
    """
    Delete all data from InfluxDB within the specified bucket.
    
    :param influx_url: InfluxDB server URL
    :param influx_token: InfluxDB authentication token
    :param influx_org: InfluxDB organization name
    :param influx_bucket: InfluxDB bucket name
    """
    # Initialize the InfluxDB client
    client = InfluxDBClient(url=influx_url, token=influx_token, org=influx_org)
    
    # Flux query to delete all data from the bucket
    delete_query = f"""
    from(bucket: "{influx_bucket}")
        |> range(start: 0)  // This ensures all data is selected, no time filter
    """
    
    try:
        # Execute the deletion
        client.query_api().query(delete_query, org=influx_org)
        print(f"All data in bucket '{influx_bucket}' deleted successfully.")
    except Exception as e:
        print(f"Error deleting data from InfluxDB: {e}")
    finally:
        # Close the client
        client.close()

def write_to_influxdb(occupancy_file, temperature_file, 
                      influx_url="http://localhost:8086", 
                      influx_token="your-influx-token", 
                      influx_org="your-organization", 
                      influx_bucket="sensor_data"):
    """
    Write sensor data from JSON files to InfluxDB after deleting all existing data
    
    :param occupancy_file: Path to occupancy data JSON file
    :param temperature_file: Path to temperature data JSON file
    :param influx_url: InfluxDB server URL
    :param influx_token: InfluxDB authentication token
    :param influx_org: InfluxDB organization
    :param influx_bucket: InfluxDB bucket name
    """
    # Read JSON files
    with open(occupancy_file, 'r') as f:
        occupancy_data = json.load(f)
    
    with open(temperature_file, 'r') as f:
        temperature_data = json.load(f)
    
    # Delete all existing data in the specified bucket
    delete_existing_data(influx_url, influx_token, influx_org, influx_bucket)

    # Create InfluxDB client
    client = InfluxDBClient(url=influx_url, token=influx_token, org=influx_org)
    write_api = client.write_api(write_options=SYNCHRONOUS)
    
    try:
        # Write Occupancy Data to InfluxDB
        for data in occupancy_data:
            occupancy_point = (
                Point("occupancy")
                .tag("room", data['room'])
                .tag("occupancy_sensor", data['occupancy_sensor'])
                .tag("ac_unit", data['ac_unit'])
                .field("occupied", data['value'])
                .time(data['time'])
            )
            write_api.write(bucket=influx_bucket, org=influx_org, record=occupancy_point)
        
        # Write Temperature Data to InfluxDB
        for data in temperature_data:
            temp_point = (
                Point("temperature")
                .tag("room", data['room'])
                .tag("temp_sensor", data['temp_sensor'])
                .tag("ac_unit", data['ac_unit'])
                .field("celsius", data['value'])
                .time(data['time'])
            )
            write_api.write(bucket=influx_bucket, org=influx_org, record=temp_point)
        
        print("Data successfully written to InfluxDB")
    
    except Exception as e:
        print(f"Error writing to InfluxDB: {e}")
    
    finally:
        # Close the client
        client.close()

# Main execution
if __name__ == "__main__":
    # Set start time to current time or a specific date
    start_time = datetime.now()
    
    # Step 1: Generate Sensor Data
    generator = SensorDataGenerator(start_time)
    sensor_data = generator.generate_sensor_data()
    
    # Step 2: Save Data to JSON Files
    occupancy_file, temperature_file = generator.save_sensor_data(sensor_data)

    # Step 3: Write to InfluxDB (optional)
    load_dotenv()

    write_to_influxdb(
        occupancy_file, 
        temperature_file,
        # Update these with your InfluxDB connection details
        influx_url=os.getenv("INFLUX_URL"),
        influx_token=os.getenv("INFLUX_TOKEN"),
        influx_org=os.getenv("INFLUX_ORG"),
        influx_bucket=os.getenv("INFLUX_BUCKET")
    )

    