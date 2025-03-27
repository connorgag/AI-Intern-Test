import json
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

class DormitoryGraphDatabase:
    def __init__(self, uri, user, password, data_file='dorms_data.json'):
        """
        Initialize the Neo4j database connection
        
        :param uri: Neo4j database URI
        :param user: Neo4j username
        :param password: Neo4j password
        :param data_file: Path to JSON configuration file
        """
        self._driver = GraphDatabase.driver(uri, auth=(user, password))
        
        # Load graph data from JSON
        with open(data_file, 'r') as f:
            self.graph_data = json.load(f)

    def close(self):
        """Close the database connection"""
        self._driver.close()

    def _generate_create_query(self):
        """
        Generate Cypher query dynamically from JSON data
        
        :return: Cypher create query string
        """
        # Create nodes and relationships dynamically
        create_nodes = []
        create_relationships = []

        # Create Room Nodes
        for room in self.graph_data['rooms']:
            create_nodes.append(f"(room_{room['roomNumber']}:Room {{roomNumber: '{room['roomNumber']}', roomType: '{room['roomType']}'}}")

        # Create AC Unit Nodes
        for ac in self.graph_data['airConditioningUnits']:
            create_nodes.append(f"(ac_{ac['label']}:AirConditioningUnit {{label: '{ac['label']}', location: '{ac['location']}'}}")
            
            # AC Unit to Room Services
            for room_number in ac['servicesRooms']:
                create_relationships.append(f"(ac_{ac['label']})-[:SERVICES]->(room_{room_number})")

        # Create Temperature Sensor Nodes
        for sensor in self.graph_data['temperatureSensors']:
            create_nodes.append(f"(tempSensor_{sensor['label']}:TemperatureSensor {{label: '{sensor['label']}', roomNumber: '{sensor['roomNumber']}'}}")
            
            # Sensor to Room and AC Unit Relationships
            create_relationships.append(f"(tempSensor_{sensor['label']})-[:MONITORS]->(room_{sensor['roomNumber']})")
            
            # Find corresponding AC Unit
            for ac in self.graph_data['airConditioningUnits']:
                if sensor['roomNumber'] in ac['servicesRooms']:
                    create_relationships.append(f"(tempSensor_{sensor['label']})-[:REPORTS_TO]->(ac_{ac['label']})")

        # Create Occupancy Sensor Nodes
        for sensor in self.graph_data['occupancySensors']:
            create_nodes.append(f"(occupancySensor_{sensor['label']}:OccupancySensor {{label: '{sensor['label']}', roomNumber: '{sensor['roomNumber']}'}}")
            
            # Sensor to Room Relationships
            create_relationships.append(f"(occupancySensor_{sensor['label']})-[:MONITORS]->(room_{sensor['roomNumber']})")

        # Combine all nodes and relationships
        full_query = "CREATE \n" + ",\n".join(create_nodes) + ",\n" + ",\n".join(create_relationships) + ";"
        return full_query

    def create_dormitory_model(self):
        """
        Create the entire dormitory graph model using dynamic query generation
        """
        create_query = self._generate_create_query()
        
        with self._driver.session() as session:
            session.run(create_query)

    def get_rooms_by_ac_unit(self, ac_unit_label):
        """
        Retrieve rooms serviced by a specific AC Unit
        
        :param ac_unit_label: Label of the AC Unit
        :return: List of room numbers
        """
        query = """
        MATCH (ac:AirConditioningUnit)-[:SERVICES]->(room:Room)
        WHERE ac.label = $ac_unit_label
        RETURN room.roomNumber
        """
        
        with self._driver.session() as session:
            result = session.run(query, ac_unit_label=ac_unit_label)
            return [record["room.roomNumber"] for record in result]

    def get_temperature_sensors_for_ac_unit(self, ac_unit_label):
        """
        Retrieve temperature sensors reporting to a specific AC Unit
        
        :param ac_unit_label: Label of the AC Unit
        :return: List of temperature sensor labels
        """
        query = """
        MATCH (tempSensor:TemperatureSensor)-[:REPORTS_TO]->(ac:AirConditioningUnit)
        WHERE ac.label = $ac_unit_label
        RETURN tempSensor.label
        """
        
        with self._driver.session() as session:
            result = session.run(query, ac_unit_label=ac_unit_label)
            return [record["tempSensor.label"] for record in result]

def main():
    load_dotenv()

    uri = os.getenv('NEO4J_URI')
    user = os.getenv('NEO4J_USER')
    password = os.getenv('NEO4J_PASSWORD')

    # Create the graph database instance
    graph_db = DormitoryGraphDatabase(uri, user, password)

    URI = uri
    AUTH = (user, password)

    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        driver.verify_connectivity()
        print("Connection established.")


    return 




    try:
        # Create the dormitory model
        graph_db.create_dormitory_model()

        # Example queries
        print("Rooms serviced by AC-Unit-M1:")
        print(graph_db.get_rooms_by_ac_unit('AC-Unit-M1'))

        print("\nTemperature sensors for AC-Unit-M2:")
        print(graph_db.get_temperature_sensors_for_ac_unit('AC-Unit-M2'))

    finally:
        # Always close the connection
        graph_db.close()

if __name__ == "__main__":
    main()