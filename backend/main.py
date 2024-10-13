from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import subprocess
import os
import time
import json
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
# from langchain.llms.llamacpp import LlamaCpp
# from langchain.prompts import PromptTemplate

# Set up the database connection
DATABASE_URL = "postgresql://postgres:yourpassword@localhost:5432/problems_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Define the models for Problem and Test Case
class Problem(Base):
    __tablename__ = "problems"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String)
    arguments = Column(String)

class TestCase(Base):
    __tablename__ = "test_cases"
    
    id = Column(Integer, primary_key=True, index=True)
    problem_id = Column(Integer, ForeignKey("problems.id"))
    inputs = Column(String)  # JSON-encoded inputs
    expected_output = Column(String)
    problem = relationship("Problem", back_populates="test_cases")

Problem.test_cases = relationship("TestCase", back_populates="problem")

# Create the tables if they don't exist
Base.metadata.create_all(bind=engine)

# Set up FastAPI and CORS middleware
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Add the origin of your frontend (adjust the port if necessary)
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

# Define the Pydantic model for code execution requests
class CodeExecutionRequest(BaseModel):
    code: str
    problem_id: int

# Fetch all problems
@app.get("/problems")
def get_problems():
    db = SessionLocal()
    problems = db.query(Problem).all()
    return [{"id": p.id, "title": p.title, "description": p.description, "arguments": p.arguments} for p in problems]

# Fetch a specific problem with its test cases
@app.get("/problems/{problem_id}")
def get_problem(problem_id: int):
    db = SessionLocal()
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    test_cases = db.query(TestCase).filter(TestCase.problem_id == problem_id).all()
    return {
        "id": problem.id,
        "title": problem.title,
        "description": problem.description,
        "arguments": problem.arguments,
        "test_cases": [
            {"inputs": json.loads(tc.inputs), "expected_output": tc.expected_output}
            for tc in test_cases
        ]
    }

# Fetch all test cases for a specific problem
@app.get("/problems/{problem_id}/test_cases")
def get_test_cases_for_problem(problem_id: int):
    db = SessionLocal()
    test_cases = db.query(TestCase).filter(TestCase.problem_id == problem_id).all()
    if not test_cases:
        raise HTTPException(status_code=404, detail="No test cases found for this problem")
    
    return [
        {"inputs": json.loads(tc.inputs), "expected_output": tc.expected_output}
        for tc in test_cases
    ]

# Add route to execute code
@app.post("/execute/")
def execute_code(request: CodeExecutionRequest):
    db = SessionLocal()
    
    # Fetch the problem and test cases from the database
    problem = db.query(Problem).filter(Problem.id == request.problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    
    test_cases = db.query(TestCase).filter(TestCase.problem_id == request.problem_id).all()
    if not test_cases:
        raise HTTPException(status_code=404, detail="No test cases found for this problem")

    # Save the user's code to a temporary file
    temp_code_file = "user_code.py"
    with open(temp_code_file, "w") as f:
        f.write(request.code)
        f.write("\n")

    # Prepare test case data to pass to code_runner.py
    test_case_data = [
        (json.loads(tc.inputs), tc.expected_output)
        for tc in test_cases
    ]

    # Save the test cases to a temporary file (to be loaded by code_runner.py)
    temp_test_case_file = "test_cases.json"
    with open(temp_test_case_file, "w") as f:
        json.dump(test_case_data, f)

    # Run the subprocess to execute the test cases via code_runner.py
    try:
        # Run the code_runner.py script and capture the output
        process = subprocess.Popen(
            ["python", "code_runner.py", temp_test_case_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        stdout, stderr = process.communicate()

        # Default result structure
        result = {"test_cases": []}

        # Parse stdout from code_runner.py (contains test case results)
        if stdout:
            try:
                parsed_output = json.loads(stdout.strip())
                result["test_cases"] = parsed_output.get("test_cases", [])
            except json.JSONDecodeError:
                result["test_cases"].append({
                    "stderr": ["Failed to parse JSON from code_runner.py"]
                })

        # If there's stderr outside of individual test cases, append it to the last test case or add a separate entry
        if stderr:
            result["test_cases"].append({
                "stderr": stderr.strip().splitlines()
            })

        print(result)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Clean up the temporary files
        if os.path.exists(temp_code_file):
            os.remove(temp_code_file)
        if os.path.exists(temp_test_case_file):
            os.remove(temp_test_case_file)
            
# Add route to generate a hint using LangChain and CodeLlama
@app.post("/generate_hint/")
def generate_hint(request: CodeExecutionRequest):
    db = SessionLocal()
    
    # Fetch the problem description from the database
    problem = db.query(Problem).filter(Problem.id == request.problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    # Execute the code to get output
    execute_response = execute_code(request)

    print(execute_response)
    
    # Combine the problem description, code, and execute output
    problem_description = problem.description
    code_output = execute_response['stdout'] + execute_response['stderr']
    user_code = request.code

    # Initialize the LLM with CodeLlama or an alternative
    # llm = LlamaCpp(
    #     model_path="/Users/rlm/Desktop/Code/llama.cpp/models/openorca-platypus2-13b.gguf.q4_0.bin",
    #     f16_kv=True,  # MUST set to True, otherwise you will run into problem after a couple of calls
    #     verbose=True,
    # )

    
    # Define a prompt to generate the hint
    prompt = f"""
    You are helping a student with the following problem:

    Problem Description: {problem_description}

    Their Code:
    {user_code}

    The output from running the code:
    {code_output}

    Based on the problem description, their code, and the output, provide a helpful hint on what might be wrong with their implementation and how they can improve it.
    """

    print(prompt)

    # Use LangChain to generate the hint
    # prompt_template = PromptTemplate.from_template(prompt)
    # hint = llm(prompt_template)

    # return {"hint": hint}

