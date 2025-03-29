from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()

# Connect to the Neo4j database
URI = os.getenv("NEO4J_URI")
AUTH = ("neo4j", "my_password")

with GraphDatabase.driver(URI, auth=AUTH) as driver:
    session = driver.session()

    # Clear the database
    session.run("MATCH (n) DETACH DELETE n")
    
    # Create rooms (6 dorms and 2 mechanical rooms)
    session.run("""
    CREATE (room1:Room {name: 'Room 1', type: 'Dorm'}),
           (room2:Room {name: 'Room 2', type: 'Dorm'}),
           (room3:Room {name: 'Room 3', type: 'Dorm'}),
           (room4:Room {name: 'Room 4', type: 'Dorm'}),
           (room5:Room {name: 'Room 5', type: 'Dorm'}),
           (room6:Room {name: 'Room 6', type: 'Dorm'}),
           (room7:Room {name: 'Room 7', type: 'Mechanical'}),
           (room8:Room {name: 'Room 8', type: 'Mechanical'})
    """)

    # Create Air Conditioning Units
    session.run("""
    CREATE (ac1:AirConditioningUnit {name: 'AC Unit 1'}),
           (ac2:AirConditioningUnit {name: 'AC Unit 2'})
    """)

    # Create relationships between rooms and air conditioning units
    session.run("""
    MATCH (room1:Room {name: 'Room 1'}), (room2:Room {name: 'Room 2'}), (room3:Room {name: 'Room 3'}), (ac1:AirConditioningUnit {name: 'AC Unit 1'})
    CREATE (ac1)-[:SERVICES]->(room1),
           (ac1)-[:SERVICES]->(room2),
           (ac1)-[:SERVICES]->(room3)
    """)

    session.run("""
    MATCH (room4:Room {name: 'Room 4'}), (room5:Room {name: 'Room 5'}), (room6:Room {name: 'Room 6'}), (ac2:AirConditioningUnit {name: 'AC Unit 2'})
    CREATE (ac2)-[:SERVICES]->(room4),
           (ac2)-[:SERVICES]->(room5),
           (ac2)-[:SERVICES]->(room6)
    """)

    # Create sensors for temperature and occupancy
    session.run("""
    CREATE (tempSensor1:TemperatureSensor {label: 'Temp Sensor 1'}),
           (tempSensor2:TemperatureSensor {label: 'Temp Sensor 2'}),
           (tempSensor3:TemperatureSensor {label: 'Temp Sensor 3'}),
           (tempSensor4:TemperatureSensor {label: 'Temp Sensor 4'}),
           (tempSensor5:TemperatureSensor {label: 'Temp Sensor 5'}),
           (tempSensor6:TemperatureSensor {label: 'Temp Sensor 6'}),
           (occSensor1:OccupancySensor {label: 'Occupancy Sensor 1'}),
           (occSensor2:OccupancySensor {label: 'Occupancy Sensor 2'}),
           (occSensor3:OccupancySensor {label: 'Occupancy Sensor 3'}),
           (occSensor4:OccupancySensor {label: 'Occupancy Sensor 4'}),
           (occSensor5:OccupancySensor {label: 'Occupancy Sensor 5'}),
           (occSensor6:OccupancySensor {label: 'Occupancy Sensor 6'})
    """)

    # Create relationships between sensors and rooms
    session.run("""
    MATCH (room1:Room {name: 'Room 1'}), (tempSensor1:TemperatureSensor {label: 'Temp Sensor 1'}), (occSensor1:OccupancySensor {label: 'Occupancy Sensor 1'})
    CREATE (room1)-[:MONITORS]->(tempSensor1),
           (room1)-[:MEASURES]->(occSensor1)
    """)

    session.run("""
    MATCH (room2:Room {name: 'Room 2'}), (tempSensor2:TemperatureSensor {label: 'Temp Sensor 2'}), (occSensor2:OccupancySensor {label: 'Occupancy Sensor 2'})
    CREATE (room2)-[:MONITORS]->(tempSensor2),
           (room2)-[:MEASURES]->(occSensor2)
    """)

    session.run("""
    MATCH (room3:Room {name: 'Room 3'}), (tempSensor3:TemperatureSensor {label: 'Temp Sensor 3'}), (occSensor3:OccupancySensor {label: 'Occupancy Sensor 3'})
    CREATE (room3)-[:MONITORS]->(tempSensor3),
           (room3)-[:MEASURES]->(occSensor3)
    """)

    session.run("""
    MATCH (room4:Room {name: 'Room 4'}), (tempSensor4:TemperatureSensor {label: 'Temp Sensor 4'}), (occSensor4:OccupancySensor {label: 'Occupancy Sensor 4'})
    CREATE (room4)-[:MONITORS]->(tempSensor4),
           (room4)-[:MEASURES]->(occSensor4)
    """)

    session.run("""
    MATCH (room5:Room {name: 'Room 5'}), (tempSensor5:TemperatureSensor {label: 'Temp Sensor 5'}), (occSensor5:OccupancySensor {label: 'Occupancy Sensor 5'})
    CREATE (room5)-[:MONITORS]->(tempSensor5),
           (room5)-[:MEASURES]->(occSensor5)
    """)

    session.run("""
    MATCH (room6:Room {name: 'Room 6'}), (tempSensor6:TemperatureSensor {label: 'Temp Sensor 6'}), (occSensor6:OccupancySensor {label: 'Occupancy Sensor 6'})
    CREATE (room6)-[:MONITORS]->(tempSensor6),
           (room6)-[:MEASURES]->(occSensor6)
    """)

    # Create relationships between air conditioning units and temperature sensors in dorm rooms
    session.run("""
    MATCH (ac1:AirConditioningUnit {name: 'AC Unit 1'}), (tempSensor1:TemperatureSensor {label: 'Temp Sensor 1'}), (tempSensor2:TemperatureSensor {label: 'Temp Sensor 2'}), (tempSensor3:TemperatureSensor {label: 'Temp Sensor 3'})
    CREATE (tempSensor1)-[:SERVICES_AC_UNIT]->(ac1),
           (tempSensor2)-[:SERVICES_AC_UNIT]->(ac1),
           (tempSensor3)-[:SERVICES_AC_UNIT]->(ac1)
    """)

    session.run("""
    MATCH (ac2:AirConditioningUnit {name: 'AC Unit 2'}), (tempSensor4:TemperatureSensor {label: 'Temp Sensor 4'}), (tempSensor5:TemperatureSensor {label: 'Temp Sensor 5'}), (tempSensor6:TemperatureSensor {label: 'Temp Sensor 6'})
    CREATE (tempSensor4)-[:SERVICES_AC_UNIT]->(ac2),
           (tempSensor5)-[:SERVICES_AC_UNIT]->(ac2),
           (tempSensor6)-[:SERVICES_AC_UNIT]->(ac2)
    """)

    print("Graph creation complete.")
