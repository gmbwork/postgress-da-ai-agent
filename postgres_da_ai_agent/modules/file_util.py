import json
import yaml

# Writes given content to a file provided in the parameters, filename and content
def write_to_file(filename, content):
    with open(filename, "w") as f:
        f.write(content)
        

# Writes given json string to a file provided in the parameters, filename and json_str
def write_to_json_file(filename, json_str: str):
    # convert ' to "
    json_str = json_str.replace("'", '"')
    
    #Convert the string to python object
    json_obj = json.loads(json_str)
    
    # Write the Python object to a file as JSON
    with open(filename, "w") as f:
        json.dump(json_obj, f, indent=4)
        
        
# Writes given json str as yaml string to a file provided in the parameters, filename and json_str
def write_to_yaml_file(filename, json_str: str):
    print("write_to_yaml_file(): ", json_str)
    
    # Try to replace single queotes with double quotes for JSON
    cleaned_json_str = json_str.replace("'", '"')
    
    print("write_to_yaml_file(): cleaned_json_str: ", cleaned_json_str)
    
    # Safely conver the JSON string to Python object
    try:
        data = json.loads(cleaned_json_str)
    except json.JSONDecodeError as e:
        print("write_to_yaml_file(): JSONDecodeError: ", e)
        return
    
    
    # Write the Python object to the file as YAML
    with open(filename, "w") as f:
        yaml.dump(data, f)