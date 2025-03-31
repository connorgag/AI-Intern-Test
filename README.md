# Digital Twin Natural Language Query Interface

Run neo4j with:
```brew services start neo4j```

Do the same thing for Influx:
```brew services start influxdb```

Then start the streamlit UI to ask questions:
```streamlit run ui.py```

You can also run queries without the UI by running:
```python3 natural_language_query.py "How many rooms are there?"```