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
    problem_id: int  # Include the problem ID with the code

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

# Fetch all test cases associated with a specific problem
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
    
    # Fetch test cases for the given problem_id
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
        process = subprocess.Popen(
            ["python", "code_runner.py", temp_test_case_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        stdout, stderr = process.communicate()

        result = {
            "stdout": [],
            "stderr": [],
            "test_cases": [],
        }

        # Handle stdout (combined test results and print output)
        if stdout:
            try:
                # Parse the JSON output from code_runner.py
                parsed_output = json.loads(stdout.strip())

                # Populate test cases and print output separately
                result["stdout"] = parsed_output.get("stdout", [])
                result["test_cases"] = parsed_output.get("test_cases", [])
            except json.JSONDecodeError:
                result["stderr"].append({
                    "timestamp": time.strftime("%H:%M:%S", time.localtime()),
                    "error": "Failed to parse JSON from code_runner.py"
                })

        # Handle stderr (errors during execution)
        if stderr:
            for line in stderr.splitlines():
                result["stderr"].append({
                    "timestamp": time.strftime("%H:%M:%S", time.localtime()),
                    "error": line
                })

        print(result)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Clean up the temporary user code file and test case file
        if os.path.exists(temp_code_file):
            os.remove(temp_code_file)
        if os.path.exists(temp_test_case_file):
            os.remove(temp_test_case_file)

# Add route to create a new problem
class ProblemRequest(BaseModel):
    title: str
    description: str
    arguments: str

@app.post("/problems")
def create_problem(problem_request: ProblemRequest):
    db = SessionLocal()
    problem = Problem(
        title=problem_request.title,
        description=problem_request.description,
        arguments=problem_request.arguments
    )
    db.add(problem)
    db.commit()
    db.refresh(problem)
    return problem

# Add route to create a test case for a specific problem
class TestCaseRequest(BaseModel):
    problem_id: int
    inputs: str  # JSON-encoded inputs
    expected_output: str

@app.post("/test_cases")
def create_test_case(test_case_request: TestCaseRequest):
    db = SessionLocal()
    test_case = TestCase(
        problem_id=test_case_request.problem_id,
        inputs=test_case_request.inputs,
        expected_output=test_case_request.expected_output
    )
    db.add(test_case)
    db.commit()
    db.refresh(test_case)
    return test_case
