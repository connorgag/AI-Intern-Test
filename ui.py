import streamlit as st
from natural_language_query import NaturalLanguageQueryProcessor
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from neo4j import GraphDatabase
from influxdb_client import InfluxDBClient
import networkx as nx
import os
from dotenv import load_dotenv

class DatabaseConnector:
    def __init__(self):
        self.neo4j_driver = None
        self.influx_client = None
        self.influx_query_api = None
    
    def connect_neo4j(self, uri, user, password):
        try:
            self.neo4j_driver = GraphDatabase.driver(uri, auth=(user, password))
            # Test the connection
            with self.neo4j_driver.session() as session:
                result = session.run("RETURN 1 AS test")
                return True, "Connected successfully to Neo4j"
        except Exception as e:
            if self.neo4j_driver:
                self.neo4j_driver.close()
                self.neo4j_driver = None
            return False, f"Neo4j connection error: {str(e)}"
    
    def connect_influxdb(self, url, token, org):
        try:
            self.influx_client = InfluxDBClient(url=url, token=token, org=org)
            self.influx_query_api = self.influx_client.query_api()
            # Test the connection
            health = self.influx_client.health()
            if health and health.status == "pass":
                return True, "Connected successfully to InfluxDB"
            return False, "InfluxDB connection failed: Health check failed"
        except Exception as e:
            if self.influx_client:
                self.influx_client.close()
                self.influx_client = None
                self.influx_query_api = None
            return False, f"InfluxDB connection error: {str(e)}"
    
    def close(self):
        if self.neo4j_driver:
            self.neo4j_driver.close()
        if self.influx_client:
            self.influx_client.close()
    
    def run_neo4j_query(self, query):
        if not self.neo4j_driver:
            raise Exception("Neo4j is not connected. Please connect first.")
            
        with self.neo4j_driver.session() as session:
            result = session.run(query)
            # Convert to list for processing
            return [record for record in result]
    
    def run_influx_query(self, query, bucket=None):
        if not self.influx_query_api:
            raise Exception("InfluxDB is not connected. Please connect first.")
        
        # If bucket is provided, make sure it's in the query
        if bucket and 'bucket:' not in query:
            query = f'from(bucket: "{bucket}")\n{query}'
            
        tables = self.influx_query_api.query(query=query)
        # Convert to DataFrame
        if tables:
            return tables.to_pandas()
        return pd.DataFrame()

# Function to visualize Neo4j graph data using networkx and plotly
def visualize_graph(neo4j_records):
    G = nx.Graph()
    
    # Extract nodes and relationships from Neo4j records
    nodes = {}
    relationships = []
    
    for record in neo4j_records:
        for key, value in record.items():
            if hasattr(value, 'id') and hasattr(value, 'labels'):  # It's a node
                node_id = value.id
                if node_id not in nodes:
                    nodes[node_id] = {
                        'id': node_id,
                        'labels': list(value.labels),
                        'properties': dict(value)
                    }
                    # Add node properties as attributes
                    node_props = dict(value)
                    node_props['labels'] = ','.join(value.labels)
                    G.add_node(node_id, **node_props)
            elif hasattr(value, 'start') and hasattr(value, 'end'):  # It's a relationship
                start_node = value.start_node.id
                end_node = value.end_node.id
                rel_type = value.type
                rel_props = dict(value)
                
                # Add the nodes if they don't exist
                if start_node not in nodes:
                    start_props = dict(value.start_node)
                    start_props['labels'] = ','.join(value.start_node.labels)
                    nodes[start_node] = {
                        'id': start_node,
                        'labels': list(value.start_node.labels),
                        'properties': start_props
                    }
                    G.add_node(start_node, **start_props)
                
                if end_node not in nodes:
                    end_props = dict(value.end_node)
                    end_props['labels'] = ','.join(value.end_node.labels)
                    nodes[end_node] = {
                        'id': end_node,
                        'labels': list(value.end_node.labels),
                        'properties': end_props
                    }
                    G.add_node(end_node, **end_props)
                
                # Add the relationship
                G.add_edge(start_node, end_node, type=rel_type, **rel_props)
                relationships.append({
                    'from': start_node,
                    'to': end_node,
                    'type': rel_type
                })
    
    # Create a network visualization
    pos = nx.spring_layout(G, seed=42)  # Fixed seed for consistent layout
    
    # Create edge traces
    edge_traces = []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        
        # Get relationship type for hover text
        rel_type = G.edges[edge].get('type', 'unknown')
        
        edge_trace = go.Scatter(
            x=[x0, x1, None],
            y=[y0, y1, None],
            line=dict(width=1, color='#888'),
            hoverinfo='text',
            text=f"Relationship: {rel_type}",
            mode='lines'
        )
        edge_traces.append(edge_trace)
    
    # Create node trace
    node_x = []
    node_y = []
    node_text = []
    node_colors = []
    
    # Color nodes by label
    label_colors = {}
    color_idx = 0
    for node, attrs in G.nodes(data=True):
        labels = attrs.get('labels', '').split(',')
        main_label = labels[0] if labels else 'Unknown'
        
        if main_label not in label_colors:
            label_colors[main_label] = color_idx
            color_idx += 1
        
        node_colors.append(label_colors[main_label])
    
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        
        # Create hover text with node properties
        properties = G.nodes[node]
        text = f"ID: {node}<br>"
        if 'labels' in properties:
            text += f"Labels: {properties['labels']}<br>"
        
        # Add other properties for hover info
        for key, value in properties.items():
            if key != 'labels' and not key.startswith('__'):
                text += f"{key}: {value}<br>"
        
        node_text.append(text)
    
    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode='markers',
        hoverinfo='text',
        text=node_text,
        marker=dict(
            showscale=True,
            colorscale='Viridis',
            size=15,
            color=node_colors,
            colorbar=dict(
                thickness=15,
                title='Node Label Groups',
                xanchor='left',
                titleside='right'
            )
        )
    )
    
    # Create figure with all traces
    fig = go.Figure(data=edge_traces + [node_trace],
                    layout=go.Layout(
                        showlegend=False,
                        hovermode='closest',
                        margin=dict(b=20, l=5, r=5, t=40),
                        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        width=1000,  # Wider plot
                        height=700,  # Taller plot
                        title="Neo4j Graph Visualization"
                    ))
    
    # Add legend for node labels
    annotations = []
    y_pos = 1.05
    for label, color_idx in label_colors.items():
        annotations.append(dict(
            x=0,
            y=y_pos,
            xref="paper",
            yref="paper",
            text=f"{label}",
            showarrow=False,
            font=dict(
                color="black"
            ),
            bgcolor=f"rgba({color_idx*30}, {255-color_idx*20}, {100+color_idx*10}, 0.5)",
            bordercolor="black",
            borderwidth=1,
            borderpad=4,
            align="left"
        ))
        y_pos -= 0.05
    
    fig.update_layout(annotations=annotations)
    
    return fig

def main():
    st.set_page_config(layout="wide")  # Use wide mode for more space
    
    st.title("Digital Twin Query Interface")
    
    # Initialize database connector in session state
    if 'db_connector' not in st.session_state:
        st.session_state.db_connector = DatabaseConnector()
    
    # Connection status in session state
    if 'neo4j_connected' not in st.session_state:
        st.session_state.neo4j_connected = False
    
    if 'influxdb_connected' not in st.session_state:
        st.session_state.influxdb_connected = False
    
    # Main application layout with tabs for different functions
    # tabs = st.tabs(["Query", "Database Connections", "Neo4j Explorer", "InfluxDB Explorer"])
    # tabs = st.tabs(["Query"])
    
    # Tab 1: Natural Language Query
    # with tabs[0]:
    st.header("Natural Language Query")
    st.write("Ask a question about the data, and we'll process it for you!")
    
    # User input
    query = st.text_input("Enter your query:")
    model = st.selectbox("Select Model:", ["gpt-4o", "gpt-4o-mini"])
    
    if st.button("Get Answer"):
        if not query:
            st.error("Please enter a query.")
        else:
            # Initialize the processor with the selected model
            processor = NaturalLanguageQueryProcessor(model=model)
            
            # Process the query using NLP
            result = processor.process_query(query)

            # Display results
            st.subheader("Natural Language Response:")
            st.write(result['formatted_response'])

            # Display raw data in tabular format
            st.subheader("Raw Data:")
            if result['raw_data']:
                if isinstance(result['raw_data'], dict):  # Handle hybrid query results
                    if 'neo4j_result' in result['raw_data'] and result['raw_data']['neo4j_result']:
                        st.write("Neo4j Results:")
                        neo4j_df = pd.DataFrame([dict(item) for item in result['raw_data']['neo4j_result']])
                        st.dataframe(neo4j_df)
                    if 'influxdb_result' in result['raw_data'] and result['raw_data']['influxdb_result']:
                        st.write("InfluxDB Results:")
                        st.dataframe(result['raw_data']['influxdb_result'])
                elif isinstance(result['raw_data'], list):
                        # Convert the list of dictionaries to a DataFrame
                    df = pd.DataFrame(result['raw_data'])
                    st.dataframe(df)
                else:
                    st.write("No data to display.")
            else:
                st.write("No data to display.")
            
            processor.close_connections()
#     # Tab 2: Database Connections
#     with tabs[1]:
#         st.header("Database Connections")
        
#         # Neo4j Connection
#         st.subheader("Neo4j Connection")
#         neo4j_uri = st.text_input("Neo4j URI", value="bolt://localhost:7687")
#         neo4j_user = st.text_input("Neo4j User", value="neo4j")
#         neo4j_password = st.text_input("Neo4j Password", value="my_password", type="password")
        
#         if st.button("Connect to Neo4j"):
#             st.session_state.neo4j_connected, neo4j_message = st.session_state.db_connector.connect_neo4j(neo4j_uri, neo4j_user, neo4j_password)
#             st.success(neo4j_message) if st.session_state.neo4j_connected else st.error(neo4j_message)
        
#         if st.session_state.neo4j_connected:
#             st.success("Connected to Neo4j")
#         else:
#             st.error("Not connected to Neo4j")
        
#         # InfluxDB Connection
#         st.subheader("InfluxDB Connection")

#         load_dotenv(dotenv_path=".env")

#         influx_url = st.text_input("InfluxDB URL", value="http://localhost:8086")
#         influx_token = st.text_input("InfluxDB Token", type="password", value=os.getenv("INFLUX_TOKEN"))
#         influx_org = st.text_input("InfluxDB Org", value="none")
#         influx_bucket = st.text_input("InfluxDB Bucket", value="bucket")
        
#         if st.button("Connect to InfluxDB"):
#             influxdb_connected, influxdb_message = st.session_state.db_connector.connect_influxdb(influx_url, influx_token, influx_org)
#             st.session_state.influxdb_connected = influxdb_connected
#             st.success(influxdb_message) if st.session_state.influxdb_connected else st.error(influxdb_message)
            
#         if st.session_state.influxdb_connected:
#             st.success("Connected to InfluxDB")
#         else:
#             st.error("Not connected to InfluxDB")
    
#     # Tab 3: Neo4j Explorer
#     with tabs[2]:
#         st.header("Neo4j Data Explorer")
#         st.write("Explore data stored in Neo4j")
        
#         if not st.session_state.neo4j_connected:
#             st.error("Not connected to Neo4j. Please connect in the 'Database Connections' tab.")
#         else:
#             neo4j_query = st.text_area("Enter Neo4j Cypher Query:", "MATCH (n) RETURN n LIMIT 10")
            
#             if st.button("Execute Neo4j Query"):
#                 try:
#                     neo4j_result = st.session_state.db_connector.run_neo4j_query(neo4j_query)
                    
#                     # Display raw results
#                     st.subheader("Raw Results")
#                     st.write(neo4j_result)
                    
#                     # Attempt to display as a graph
#                     st.subheader("Graph Visualization")
#                     if neo4j_result:
#                         fig = visualize_graph(neo4j_result)
#                         st.plotly_chart(fig)
#                     else:
#                         st.write("No data to visualize.")
                    
#                     # Convert to DataFrame and display
#                     st.subheader("Tabular Data")
#                     if neo4j_result:
#                         df = pd.DataFrame([record.data() for record in neo4j_result])
#                         st.dataframe(df)
#                     else:
#                         st.write("No results to display in table format.")
                    
#                 except Exception as e:
#                     st.error(f"Error executing query: {e}")
    
#     # Tab 4: InfluxDB Explorer
#     with tabs[3]:
#         st.header("InfluxDB Data Explorer")
#         st.write("Explore data stored in InfluxDB")
        
#         if not st.session_state.influxdb_connected:
#             st.error("Not connected to InfluxDB. Please connect in the 'Database Connections' tab.")
#         else:
#             influx_query = st.text_area("Enter InfluxDB Flux Query:", 
# """
# from(bucket: "bucket")
#     |> range(start: -1d)
#     |> filter(fn: (r) => r._measurement == "temperature" and r.room == "dorm1")
#     |> filter(fn: (r) => r._field == "celsius")
# """
#             )
            
#             if st.button("Execute InfluxDB Query"):
#                 try:
#                     influxdb_result = st.session_state.db_connector.run_influx_query(influx_query, bucket=influx_bucket)
                    
#                     # Display results
#                     st.subheader("Query Results")
#                     if not influxdb_result.empty:
#                         st.dataframe(influxdb_result)
                        
#                         # Attempt to create a simple line chart if possible
#                         st.subheader("Time Series Visualization")
#                         # Check for a time column
#                         time_col = None
#                         for col in influxdb_result.columns:
#                             if 'time' in col.lower():
#                                 time_col = col
#                                 break
                        
#                         if time_col:
#                             try:
#                                 # Try a simple line plot with the first numerical column (excluding time)
#                                 numerical_cols = influxdb_result.select_dtypes(include=['number']).columns
#                                 if len(numerical_cols) > 0:
#                                     first_num_col = numerical_cols[0]
#                                     fig = px.line(influxdb_result, x=time_col, y=first_num_col,
#                                                   title=f"Time Series of {first_num_col}")
#                                     st.plotly_chart(fig)
#                                 else:
#                                     st.warning("No numerical data found for plotting.")
#                             except Exception as plot_err:
#                                 st.error(f"Error creating plot: {plot_err}")
#                         else:
#                             st.warning("No time column found for plotting.")
#                     else:
#                         st.write("No results to display.")
                        
#                 except Exception as e:
#                     st.error(f"Error executing query: {e}")
    
    # Close connections when the app ends (optional, Streamlit usually manages this)
    # st.session_state.db_connector.close()

if __name__ == "__main__":
    main()
