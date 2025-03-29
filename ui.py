import streamlit as st
from natural_language_query import NaturalLanguageQueryProcessor


def main():
    st.title("Digital Twin Query Interface")
    st.write("Ask a question about the data, and we'll process it for you!")
    
    # User input
    query = st.text_input("Enter your query:")
    model = st.selectbox("Select Model:", ["gpt-4o", "gpt-4o-mini"])
    
    if st.button("Submit Query"):
        if query:
            # Initialize processor
            processor = NaturalLanguageQueryProcessor(model=model)
            
            # Process the query
            result = processor.process_query(query)
            
            st.write("**Answer:**", result)
            
            # Close connections
            processor.close_connections()
        else:
            st.warning("Please enter a query before submitting.")

if __name__ == "__main__":
    main()
