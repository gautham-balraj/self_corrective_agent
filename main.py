from groq import Groq
from dotenv import load_dotenv
from langchain_core.pydantic_v1 import BaseModel, Field
import os 
import subprocess
import sys
from textwrap import dedent
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser,CommaSeparatedListOutputParser
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from colour_print import *

user_goal = "provide a python code to print the 10 numbers from the fibonacci series that are divisible by 5"

load_dotenv()
api_key =  os.environ.get('GROQ_API_KEY')

# set up groq client:
client = Groq(
    api_key=api_key,
)
llm = ChatGroq(
            temperature=0,
            model_name="mixtral-8x7b-32768",
            streaming=True
        )

# system messages
# {{ this is for initial code generation  }}
system_message_1 = "You are a super creative expert in python , user task to provide a best python code to accomplish the given user goal "
human_message_1 =dedent(
    """"
    Based on the user query, provide the python code to solve the given problem.
    -------- User query------
    {user_goal}
    ------------------------
    - DO NOT provide any explanation just provide the python code 
    - Dont add any preamble in the response \n:""" )


# {{ this is for removing the unneccessary text from the code}}

system_message_2 = "You are a expert in python , user task to remove all text that are not needed to run the python code: "

human_message_2 =dedent(
    """"
    Based on the provided python code, remove all text that are not needed to run the python code.
    - check for any syntax errors, if any fix those errors 
    -------- code ------
    {code}
    ------------------------
    - DO NOT provide any explanation just provide the python code 
    - just provide the python code 
    - Dont add any preamble in the response
    - provide the complete code \n:""" )

# {{ this is for checking the dependencies and create a req.txt file}}

system_message_3 = "You are a expert python programmer "
human_message_3 =dedent(
    """"
    Based on the user code , You have to check import statements if there are any and list all the necessary libararies needed to installed
    - Dont add any preamble in the response 
    -------- code------
    {code}
    ------------------------
    - just find the libararies needed to install inorder to run the script
    - Dont add any preamble in the response 
    - if there is any libraries need to be installed reespond in the following format
    \n:
    {format_instructions}""" )

## {{ this is for fixing the errors in the code}}

system_message_4 = "You are a expert python programmer you're task to fix the errors in the code"
human_message_4 =dedent(
    """"
    Based on the user code , and the error message you have to fix the errors in the code
    - fix the errors and provide the corrected code 
    user goal:
    {user_goal}
    code:
    {code}
    error:
    {error_msg}
    -dont add any preamble in the response
    -fix the error and provide the corrected code
    - do not add any explanation just provide the corrected code\n:""" )



def fetch_from_script(file_path):
    try:
        with open(file_path, "r") as file:
            file_contents = file.read()
            return file_contents
    except FileNotFoundError:
        print(f"File '{file_path}' not found.")

# TO check whether the coding is required or not  {{  PHASE 1   }}

# create a pydantic objecet for ouput parsing
class grade(BaseModel):
    """"
    Boolean value indicating whether the given user query requires python code to generate the better response     
    """
    code : bool = Field(description="Validation score 'True' or 'False'")
    






def require_coding(query:str):
    """
    Determine whether the given user query requires python code to generate the better response
    """
    parser =  JsonOutputParser(pydantic_object=grade)
    prompt = PromptTemplate(
        template=dedent(
        """"
        Based on the user query, determine whether it is beneficial to use python code to generate a better response.
        -Respond True if it is beneficial to use python code to generate a better response, otherwise respond False.
        -Is there any calculation or similar needed to be performed repond True 
        -------- User query------
        {query}
        ------------------------
        Provide the Boolean value as a JSON,
        DO NOT provide any explanation and use these instructons to format the output  \n: 
        {format_instructions}"""),
        
    input_variables=["query"],
    partial_variables={"format_instructions": parser.get_format_instructions()})
    
    chain = prompt | llm | parser
    response = chain.invoke(
        {
            "query": query,
            "fromat_instructions":parser.get_format_instructions()
        }
    )

    
    return response['code']


# TO generate the python code for the given user query {{  PHASE 2   }}




def initial_code_creation(user_goal:str):
    prompt = ChatPromptTemplate.from_messages([("system", system_message_1), ("human", human_message_1)])
    chain = prompt | llm 
    response = chain.invoke(
    {
        "user_goal": user_goal
    })
    return response.content

def code_preproceess(initial_code:str):
    prompt = ChatPromptTemplate.from_messages([("system", system_message_2), ("human", human_message_2)])
    chain = prompt | llm 
    response = chain.invoke(
    {
        "code": initial_code
    })
    return response.content

def clean_code(code:str):
    clean_code = code.replace("```python","").replace("```","")
    return clean_code


def save_code_to_file(code: str, file_name: str = "generated_code.py"):
    with open(file_name, "w") as file:
        file.write(code)
    return file_name
    
    
        
def code_generation(user_goal:str):
  
    initial_code = initial_code_creation(user_goal)
    code = code_preproceess(initial_code)
    code = clean_code(code)
    file_name = save_code_to_file(code)
    print_white(f"Python code generated and saved to {file_name}")

    return file_name

## TO run find and fix dependencies and create a req.txt file {{  PHASE 3   }}




def execute_python_file_in_conda_env(file_path, conda_env_name='genai'):
    try:
        # Execute the Python file within the specified Conda environment
        result = subprocess.run(["conda", "run", "-n", conda_env_name, "python", file_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True)
        print("stdout:", result.stdout)  # Print stdout
      #  print("stderr:", result.stderr)  # Print stderr
        return True, result.stdout  # Execution successful, return stdout
    except subprocess.CalledProcessError as e:
        # If an error occurs during execution, return False along with the error message
        return False, e.stderr

def find_import_statements(script):
    # Split the script into lines
    lines = script.split('\n')
    
    # Check each line for import statements
    for line in lines:
        if line.strip().startswith("import ") or line.strip().startswith("from "):
            return True  # Found an import statement
    return False  # No import statements found



def findall_dependencies(file_path):
    try:
        with open(file_path, "r") as file:
            file_contents = file.read()
        
    except FileNotFoundError:
        print(f"File '{file_path}' not found.")
    
    output_parser = CommaSeparatedListOutputParser()
    prompt = ChatPromptTemplate.from_messages([("system", system_message_3), ("human", human_message_3)])
    chain = prompt | llm | output_parser
    response = chain.invoke(
        {
            "code": file_contents,
            "format_instructions":output_parser.get_format_instructions()
        }
    )
    return response


def create_txt_file(values: list, file_name: str = "requirements.txt"):
    # Split the comma-separated values
    # value_list = values.split(",")

    # Write each value to the text file
    with open(file_name, "w") as file:
        for value in values:
            file.write(value.strip() + "\n")

    print(f"Values written to {file_name}")

def install_packages_from_requirements(requirements_file='requirements.txt',conda_env_name='genai' ):
    try:
        # Create a new Conda environment from the requirements file
        subprocess.run(["conda", "create", "--name", conda_env_name, "--file", requirements_file, "-y"], check=True)
        
        print(f"Conda environment '{conda_env_name}' created successfully from '{requirements_file}'.")
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while creating Conda environment: {e}")

# wrapper function to find dependencies:
def dependencies(file_path):
    try:
        with open(file_path, "r") as file:
            file_contents = file.read()
        
    except FileNotFoundError:
        print(f"File '{file_path}' not found.")
        
    if find_import_statements(file_contents):
        dependencies = findall_dependencies(file_path)
        create_txt_file(dependencies)
        install_packages_from_requirements()  # to install the packages from the requirements.txt file
    else:
        print("No import statements found in the script.")



## find and fix :


def pip_install_missing_module(module_name, conda_env_name="genai"):
    try:
        # Install the missing module into the specified Conda environment using pip
        subprocess.run(["conda", "run", "-n", conda_env_name, "pip", "install", module_name], check=True)
        print(f"Module '{module_name}' installed successfully into Conda environment '{conda_env_name}'.")
        with open("requirements.txt", "a") as file:
            file.write(module_name + "\n")
        print(f"Module '{module_name}' appended to 'requirements.txt'.")
    except subprocess.CalledProcessError as e:
        print_red(f"Error occurred while installing module '{module_name}': {e}")
        
def execute_fix_dependencies(file_path, conda_env_name= 'genai'):
    try:
        # Execute the Python file within the specified Conda environment
        result = subprocess.run(["conda", "run", "-n", conda_env_name, "python", file_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True)
        return True, result.stdout  # Execution successful, return stdout
    except subprocess.CalledProcessError as e:
        error_message = e.stderr
        # If module not found error, install the missing module and retry execution
        if "ModuleNotFoundError" in error_message:
            module_name = error_message.split("'")[1]
            remove_start_end_underscores = lambda string: string.strip('_')
            module_name = remove_start_end_underscores(module_name)
            print(f"Module '{module_name}' not found in Conda environment '{conda_env_name}'. Installing...")
            pip_install_missing_module(module_name)
            # Retry execution after installing the missing module
            return execute_fix_dependencies(file_path)
        else:
            # If an error occurs during execution other than module not found, return False along with the error message
            return False, error_message
        
        
def find_and_fix_dependencies(file_path):
    
    file_content = fetch_from_script(file_path)
    
    if find_import_statements(file_content):
    
        success, output = execute_fix_dependencies(file_path)
        if success:
            print_magenta("all dependencies are installed")
        # else:   
        #     print_red(f"Execution failed with error: {output}")
    else:
        print_yellow("No dependency issues found in the script.")    
        
# self correction of the code {{  PHASE 4   }}

def execute_python_file_in_conda_env(file_path, conda_env_name='genai'):
    try:
        # Execute the Python file within the specified Conda environment
        command = f"conda run -n {conda_env_name} python {file_path}"
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True, shell=True)
        #print("stdout:", result.stdout)  # Print stdout
      #  print("stderr:", result.stderr)  # Print stderr
        return True, result.stdout  # Execution successful, return stdout
    except subprocess.CalledProcessError as e:
        # If an error occurs during execution, return False along with the error message
        return False, e.stderr


def self_correct_code(user_goal,code,error):
    prompt = ChatPromptTemplate.from_messages([("system", system_message_4), ("human", human_message_4)])
    chain = prompt | llm 
    response = chain.invoke(
    {
        "user_goal": user_goal,
        "code":code,
        "error_msg":error
    })
    return response.content


def execute_code_with_self_correction(user_goal,file_path,max_attempts = 5):
    print(f"Attempting to execute the code in '{file_path}'...")
    for attempt in range(max_attempts):
        success, output = execute_python_file_in_conda_env(file_path)
        if success:
            print_green(f"Execution successful! :: {output}")
            
            return True
        else:
            print_red(f"Execution failed with error: {output}")
            if attempt < max_attempts - 1:
                print_yellow(f"Attempting to self-correct the code (attempt {attempt + 1})...")
                code = fetch_from_script(file_path)
                error = output
                if "ModuleNotFoundError" in error:
                    find_and_fix_dependencies(file_path)
                else:
                    
                    corrected_code = self_correct_code(user_goal,code,error),
                    code = code_preproceess(corrected_code)
                    code = clean_code(code)
                    print(f"{attempt+1}>>>     {code}")
                    save_code_to_file(code, file_path)
                print_yellow(f"Code self-corrected (attempt {attempt + 1}). Retrying execution...")
            else:
                print_red("Maximum attempts reached. Self-correction failed.")
                return False
    
    
    
    
    
    
    
    
user_goal = """"can u provide a graph of the price of tesla stock over the last 30 days?"""

if __name__ == "__main__":

    decision_for_coding = require_coding(user_goal)
    print(decision_for_coding)
    if True:
        print_green("Python code is required to generate the better response")
        file_path = code_generation(user_goal)     
        find_and_fix_dependencies("generated_code.py")
        
        max_attempts = 5
        
        if not execute_code_with_self_correction(user_goal,file_path,max_attempts):
            print_red("Execution failed after self-correction.")

        

  