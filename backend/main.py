from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import subprocess
import os
import time
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Add the origin of your frontend (adjust the port if necessary)
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)
<<<<<<< HEAD

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
=======

class CodeExecutionRequest(BaseModel):
    code: str

@app.post("/execute/")
def execute_code(request: CodeExecutionRequest):
    # Save the user's code to a temporary file
    temp_code_file = "user_code.py"
    
    with open(temp_code_file, "w") as f:
        f.write(request.code)
        f.write("\n")

    # Run the subprocess to execute the test cases via code_runner.py
    try:
        process = subprocess.Popen(
            ["python", "code_runner.py"],
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
        # Clean up the temporary user code file
        if os.path.exists(temp_code_file):
            os.remove(temp_code_file)
