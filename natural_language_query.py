import argparse
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from neo4j import GraphDatabase
from influxdb_client import InfluxDBClient
import openai
import json
import streamlit as st

# Check if Streamlit secrets should be used (set this flag to True or False)
USE_STREAMLIT_SECRETS = True  # Set this based on your condition

if USE_STREAMLIT_SECRETS:
    # Use Streamlit secrets
    openai.api_key = st.secrets["openai"]["OPENAIAPI_KEY"]
    
    # Neo4j connection
    NEO4J_URI = st.secrets["neo4j"]["uri"]
    NEO4J_USER = st.secrets["neo4j"]["user"]
    NEO4J_PASSWORD = st.secrets["neo4j"]["password"]
    
    # InfluxDB connection
    INFLUX_URL = st.secrets["influxdb"]["url"]
    INFLUX_TOKEN = st.secrets["influxdb"]["token"]
    INFLUX_ORG = st.secrets["influxdb"]["org"]
    INFLUX_BUCKET = st.secrets["influxdb"]["bucket"]
else:
    # Load environment variables
    load_dotenv(dotenv_path=".env")

    # Configure OpenAI API
    openai.api_key = os.getenv("OPENAIAPI_KEY")

    # Database connection parameters
    NEO4J_URI = "bolt://localhost:7687"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "my_password"

    INFLUX_URL = "http://localhost:8086"
    INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
    INFLUX_ORG = os.getenv("INFLUX_ORG", "none")
    INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "bucket")


class NaturalLanguageQueryProcessor:
    def __init__(self, model):
        # Initialize connections to both databases
        self.init_neo4j()
        self.init_influxdb()
        self.model = model

    def init_neo4j(self):
        """Initialize Neo4j connection"""
        try:
            self.neo4j_driver = GraphDatabase.driver(
                NEO4J_URI, 
                auth=(NEO4J_USER, NEO4J_PASSWORD)
            )
            print("Connected to Neo4j database")
            
            # Get Neo4j schema to help with query generation
            with self.neo4j_driver.session() as session:
                self.neo4j_schema = self.get_neo4j_schema(session)
            
        except Exception as e:
            print(f"Failed to connect to Neo4j: {e}")
            self.neo4j_driver = None
    
    def init_influxdb(self):
        """Initialize InfluxDB connection"""
        try:
            self.influx_client = InfluxDBClient(
                url=INFLUX_URL,
                token=INFLUX_TOKEN,
                org=INFLUX_ORG
            )
            print("Connected to InfluxDB database")
            
            # Get InfluxDB schema information
            self.influx_schema = self.get_influxdb_schema()
            
        except Exception as e:
            print(f"Failed to connect to InfluxDB: {e}")
            self.influx_client = None
    
    def get_neo4j_schema(self, session):
        """Get detailed Neo4j schema information with sample data"""
        schema_info = {}
        
        # Get node labels
        node_labels_result = session.run("CALL db.labels()")
        node_labels = [record["label"] for record in node_labels_result]
        schema_info["node_labels"] = node_labels
        
        # Get relationship types
        rel_types_result = session.run("CALL db.relationshipTypes()")
        relationship_types = [record["relationshipType"] for record in rel_types_result]
        schema_info["relationship_types"] = relationship_types
        
        # Get detailed node information with properties and values
        node_details = {}
        for label in node_labels:
            # Get property keys for this node type
            props_query = f"""
            MATCH (n:{label}) 
            WITH n LIMIT 5
            UNWIND keys(n) AS key
            RETURN DISTINCT key
            """
            props_result = session.run(props_query)
            property_keys = [record["key"] for record in props_result]
            
            # Get sample nodes with properties
            sample_query = f"""
            MATCH (n:{label}) 
            RETURN n LIMIT 3
            """
            sample_result = session.run(sample_query)
            samples = []
            for record in sample_result:
                node = record["n"]
                samples.append(dict(node))
            
            node_details[label] = {
                "property_keys": property_keys,
                "samples": samples
            }
        
        schema_info["node_details"] = node_details
        
        # Get relationship details
        rel_details = {}
        for rel_type in relationship_types:
            # Get sample relationships
            rel_query = f"""
            MATCH ()-[r:{rel_type}]->() 
            RETURN DISTINCT startNode(r), type(r), endNode(r) LIMIT 3
            """
            rel_result = session.run(rel_query)
            samples = []
            for record in rel_result:
                start_node = dict(record["startNode(r)"])
                end_node = dict(record["endNode(r)"])
                rel_info = {
                    "start_node": start_node,
                    "relationship_type": record["type(r)"],
                    "end_node": end_node
                }
                samples.append(rel_info)
            
            rel_details[rel_type] = {
                "samples": samples
            }
        
        schema_info["relationship_details"] = rel_details
        
        return schema_info
    
    def get_influxdb_schema(self):
        """Get InfluxDB schema information to help with query generation"""
        try:
            # Get available measurements
            query_api = self.influx_client.query_api()
            measurements_query = f'import "influxdata/influxdb/schema" schema.measurements(bucket: "{INFLUX_BUCKET}")'
            measurements_result = query_api.query(query=measurements_query, org=INFLUX_ORG)
            
            measurements = []
            for table in measurements_result:
                for record in table.records:
                    measurements.append(record.values.get("_value"))
            
            # Get fields and tags for each measurement
            schema_info = {}
            for measurement in measurements:
                # Get fields
                fields_query = f'''
                import "influxdata/influxdb/schema"
                schema.measurementFieldKeys(
                    bucket: "{INFLUX_BUCKET}",
                    measurement: "{measurement}"
                )
                '''
                fields_result = query_api.query(query=fields_query, org=INFLUX_ORG)
                
                fields = []
                for table in fields_result:
                    for record in table.records:
                        fields.append(record.values.get("_value"))
                
                # Get tags
                tags_query = f'''
                import "influxdata/influxdb/schema"
                schema.measurementTagKeys(
                    bucket: "{INFLUX_BUCKET}",
                    measurement: "{measurement}"
                )
                '''
                tags_result = query_api.query(query=tags_query, org=INFLUX_ORG)
                
                tags = []
                for table in tags_result:
                    for record in table.records:
                        tags.append(record.values.get("_value"))
                
                # Get sample data for this measurement
                sample_query = f'''
                from(bucket: "{INFLUX_BUCKET}")
                    |> range(start: -30d)
                    |> filter(fn: (r) => r._measurement == "{measurement}")
                    |> limit(n: 5)
                '''
                sample_result = query_api.query(query=sample_query, org=INFLUX_ORG)
                
                samples = []
                for table in sample_result:
                    for record in table.records:
                        samples.append(record.values)
                
                schema_info[measurement] = {
                    "fields": fields,
                    "tags": tags,
                    "samples": samples[:3]  # Limit to 3 samples
                }
            
            return {
                "measurements": measurements,
                "schema": schema_info
            }
            
        except Exception as e:
            print(f"Error fetching InfluxDB schema: {e}")
            return {"measurements": [], "schema": {}}

    def determine_database(self, query):
        """Determine which database should handle the query using LLM"""
        # Simplified schema information for routing decision
        neo4j_simple_schema = {
            "node_labels": self.neo4j_schema["node_labels"],
            "relationship_types": self.neo4j_schema["relationship_types"]
        }
        
        influxdb_simple_schema = {
            "measurements": self.influx_schema["measurements"]
        }
        
        # Convert to JSON for cleaner formatting
        neo4j_schema_json = json.dumps(neo4j_simple_schema, indent=2)
        influxdb_schema_json = json.dumps(influxdb_simple_schema, indent=2)
        
        prompt = f"""Given the following database schemas and user query, determine which database should handle the query.
        
Neo4j is a graph database that stores relationships between entities. It is good for queries about relationships, connections, and structural data.
Schema: {neo4j_schema_json}

InfluxDB is a time-series database that stores measurements over time. It is good for queries about sensor data, measurements, and time-based analysis.
Schema: {influxdb_schema_json}

User query: "{query}"

Output only one of these options: "neo4j", "influxdb", or "hybrid" (if both databases are needed).
"""
        print(prompt)
        try:
            response = openai.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=10
            )
            
            database_choice = response.choices[0].message.content.strip().lower()
            
            if database_choice in ["neo4j", "influxdb", "hybrid"]:
                return database_choice
            else:
                print(f"Unexpected database choice: {database_choice}. Defaulting to Neo4j.")
                return "neo4j"
                
        except Exception as e:
            print(f"Error determining database: {e}")
            # Default to Neo4j if there's an error
            return "neo4j"
    
    def generate_neo4j_query(self, natural_language_query):
        """Generate a Cypher query from natural language using LLM with detailed schema info"""
        # Extract key schema information for better query generation
        node_details = {}
        for label, details in self.neo4j_schema["node_details"].items():
            if details["samples"]:
                node_details[label] = {
                    "property_keys": details["property_keys"],
                    "sample": details["samples"][0]  # Just one sample
                }
        
        # Prepare relationship examples
        rel_examples = []
        for rel_type, details in self.neo4j_schema["relationship_details"].items():
            if details["samples"]:
                rel_examples.append(details["samples"][0])  # Just one sample
        
        # Create a simplified schema representation
        schema_for_llm = {
            "node_types_with_properties": node_details,
            "relationship_examples": rel_examples[:3]  # Limit to 3 relationship examples
        }
        
        # Convert to JSON for cleaner formatting
        schema_json = json.dumps(schema_for_llm, indent=2)
        
        prompt = f"""Generate a Cypher query for Neo4j that accurately answers the natural language query.

Neo4j DATABASE SCHEMA (with sample data):
{schema_json}

IMPORTANT NOTES:
1. Pay attention to exact property names and capitalization in the schema
2. Be aware of the exact relationship types shown in the examples
3. When filtering by property values, respect the case sensitivity shown in the samples

Natural Language Query: "{natural_language_query}"

Return ONLY the executable Cypher query with no additional explanation or text.
"""
        
        try:
            response = openai.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            
            cypher_query = response.choices[0].message.content.strip()
            
            # Clean up the query if it's wrapped in backticks
            if cypher_query.startswith("```") and cypher_query.endswith("```"):
                cypher_query = cypher_query[3:-3].strip()
            if cypher_query.startswith("```cypher") and cypher_query.endswith("```"):
                cypher_query = cypher_query[9:-3].strip()
                
            return cypher_query
            
        except Exception as e:
            print(f"Error generating Cypher query: {e}")
            return None
    
    def generate_influxdb_query(self, natural_language_query):
        """Generate a Flux query for InfluxDB from natural language using LLM with detailed schema"""
        # Extract key schema information for better query generation
        measurements_with_samples = {}
        for measurement, details in self.influx_schema["schema"].items():
            measurements_with_samples[measurement] = {
                "fields": details["fields"],
                "tags": details["tags"],
                "samples": details["samples"][:1]  # Just one sample
            }
        
        # Create a simplified schema representation
        schema_for_llm = {
            "bucket": INFLUX_BUCKET,
            "measurements_with_samples": measurements_with_samples
        }
        
        # Convert to JSON for cleaner formatting
        print(f"Schema for LLM: {schema_for_llm}")
        schema_json = json.dumps(schema_for_llm, indent=2, default=str)
        
        prompt = f"""Generate a Flux query for InfluxDB that accurately answers the natural language query.

InfluxDB SCHEMA (with sample data):
{schema_json}

IMPORTANT NOTES:
1. Pay attention to exact measurement names, field names, and tag names in the schema
2. Use the correct bucket name: "{INFLUX_BUCKET}"
3. Always include a time range in your queries using range()
4. For default time ranges, use the last 7 days if not specified in the query
5. Make a query that returns the smallest amount of data possible
6. When asked about trends in the data, aggregate by hour to avoid too much data in the output

Natural Language Query: "{natural_language_query}"

Return ONLY the executable Flux query with no additional explanation or text.
"""
        
        try:
            response = openai.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            
            flux_query = response.choices[0].message.content.strip()
            
            # Clean up the query if it's wrapped in backticks
            if flux_query.startswith("```") and flux_query.endswith("```"):
                flux_query = flux_query[3:-3].strip()
            if flux_query.startswith("```flux") and flux_query.endswith("```"):
                flux_query = flux_query[7:-3].strip()

            flux_query = flux_query.lstrip()  # Remove leading spaces
            if flux_query.startswith("flux"):  # Ensure it starts with "flux"
                flux_query = flux_query[4:].lstrip()

            return flux_query
            
        except Exception as e:
            print(f"Error generating Flux query: {e}")
            return None
    
    def execute_neo4j_query(self, cypher_query):
        """Execute a Cypher query against Neo4j"""
        if not self.neo4j_driver:
            return "Neo4j connection not available"
        
        try:
            with self.neo4j_driver.session() as session:
                result = session.run(cypher_query)
                records = [record.data() for record in result]
                return records
        except Exception as e:
            print(f"Error executing Neo4j query: {e}")
            return []
    
    def execute_influxdb_query(self, flux_query):
        """Execute a Flux query against InfluxDB"""
        if not self.influx_client:
            return "InfluxDB connection not available"
        
        try:
            query_api = self.influx_client.query_api()
            result = query_api.query(org=INFLUX_ORG, query=flux_query)
            
            records = []
            for table in result:
                for record in table.records:
                    records.append(record.values)
            
            return records
        except Exception as e:
            print(f"Error executing InfluxDB query: {e}")
            return []
    
    def format_response(self, query_result, original_query):
        """Format database result into natural language using LLM"""
        prompt = f"""Given the following database query result and the original natural language query, 
generate a simple, concise natural language response that answers the user's question directly.

Original query: "{original_query}"

Database result: {query_result}

Format your response to be clear, concise, and directly answer the question.
"""
        
        try:
            response = openai.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            
            formatted_response = response.choices[0].message.content.strip()
            return formatted_response
            
        except Exception as e:
            print(f"Error formatting response: {e}")
            # Provide a basic formatted response if LLM fails
            return f"Results: {query_result}"
    
    def process_query(self, natural_language_query):
        """Process a natural language query and return results"""
        # Step 1: Determine which database to query
        database_type = self.determine_database(natural_language_query)
        print(f"Query will be processed using: {database_type}")
        
        # Step 2: Generate and execute query based on database type
        if database_type == "neo4j":
            # Generate and execute Neo4j query
            cypher_query = self.generate_neo4j_query(natural_language_query)
            print(f"Generated Cypher query: {cypher_query}")
            
            result = self.execute_neo4j_query(cypher_query)
            
        elif database_type == "influxdb":
            # Generate and execute InfluxDB query
            flux_query = self.generate_influxdb_query(natural_language_query)
            print(f"Generated Flux query: {flux_query}")
            
            result = self.execute_influxdb_query(flux_query)
            
        elif database_type == "hybrid":
            # Handle hybrid queries (this is a simplified approach)
            # In a real-world scenario, this would be more complex
            # First, try Neo4j
            cypher_query = self.generate_neo4j_query(natural_language_query)
            print(f"Generated Cypher query: {cypher_query}")
            neo4j_result = self.execute_neo4j_query(cypher_query)
            
            # Then, try InfluxDB
            flux_query = self.generate_influxdb_query(natural_language_query)
            print(f"Generated Flux query: {flux_query}")
            influx_result = self.execute_influxdb_query(flux_query)
            
            # Combine results
            result = {
                "neo4j_result": neo4j_result,
                "influxdb_result": influx_result
            }
        
        # Step 3: Format the response
        formatted_response = self.format_response(result, natural_language_query)
        return formatted_response
    
    def close_connections(self):
        """Close database connections"""
        if self.neo4j_driver:
            self.neo4j_driver.close()
        
        if self.influx_client:
            self.influx_client.close()


def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Process natural language queries for Neo4j and InfluxDB')
    parser.add_argument('query', type=str, help='Natural language query to process')
    parser.add_argument('--model', type=str, help='Model to use', default='gpt-4o')
    args = parser.parse_args()
    
    # Initialize the processor
    processor = NaturalLanguageQueryProcessor(model=args.model)
    
    try:
        # Process the query
        result = processor.process_query(args.query)
        print(f"Query: {args.query}")
        print(f"Answer: {result}")
    finally:
        # Close database connections
        processor.close_connections()


if __name__ == "__main__":
    main()