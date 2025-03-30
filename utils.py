import re

def read_file(file_name):
    try:
        with open(file_name, 'r') as file:
            content = file.read()
        return content
    except FileNotFoundError:
        return f"Error: The file {file_name} was not found."
    except Exception as e:
        return f"An error occurred: {e}"