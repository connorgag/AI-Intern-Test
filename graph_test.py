from neo4j import GraphDatabase

# URI examples: "neo4j://localhost", "neo4j+s://xxx.databases.neo4j.io"
URI = "bolt://localhost:7687"
AUTH = ("neo4j", "my_password")

with GraphDatabase.driver(URI, auth=AUTH) as driver:
    driver.verify_connectivity()