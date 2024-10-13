from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
import subprocess
import os
import json
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from llama_cpp import Llama

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

# Define the Pydantic model for code execution requests
class CodeExecutionRequest(BaseModel):
    code: str
    problem_id: int

# Lifespan context manager to load and unload the LLM model
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the LLM model on app startup and attach it to the app
    app.ml_models = {}
    app.ml_models["llama_model"] = Llama(
        model_path="C:/Users/chowd/ProgrammingProjects/AlgoEasy/backend/codellama-7b-python.Q4_K_S.gguf",
        f16_kv=True,  # MUST set to True to avoid issues after a few calls
        verbose=True,
        chat_format="chatml",
        n_ctx=1024,
        n_gpu_layers=20
    )
    print("Llama model loaded.")
    yield
    # Clean up LLM model on shutdown
    del app.ml_models["llama_model"]
    app.ml_models.clear()
    print("Llama model unloaded.")

# Set up FastAPI with lifespan
app = FastAPI(lifespan=lifespan)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Add the origin of your frontend (adjust the port if necessary)
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

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
        (json.loads(tc.inputs), str(tc.expected_output))
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

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Clean up the temporary files
        if os.path.exists(temp_code_file):
            os.remove(temp_code_file)
        if os.path.exists(temp_test_case_file):
            os.remove(temp_test_case_file)

# Add route to generate a hint using the pre-loaded Llama model
@app.post("/generate_hint/")
def generate_hint(request: CodeExecutionRequest):
    db = SessionLocal()
    
    # Fetch the problem description from the database
    problem = db.query(Problem).filter(Problem.id == request.problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    # Execute the code to get output
    execute_response = execute_code(request)
    
    failing_test_case = None
    # Get the first test case's results from the execution response
    for case in execute_response['test_cases']:
        print(case)
        if case['test_result']['passed'] == False:
            failing_test_case = case

    if not failing_test_case:
        raise HTTPException(status_code=500, detail="No test case results found")

    # Extract stdout and stderr from the first test case
    stdout = failing_test_case.get('stdout', [])
    stderr = failing_test_case.get('stderr', [])

    # Combine the problem description, user code, and the first test case's output
    problem_description = problem.description
    code_output = "\n".join(stdout + stderr)
    user_code = request.code

    # Add test case data
    failed_input = str(failing_test_case['test_result']['inputs'])
    failed_expected = str(failing_test_case['test_result']['expected'])
    failed_result = str(failing_test_case['test_result']['result'])

    # Access the pre-loaded Llama model from the app state
    llm = app.ml_models["llama_model"]

    # Define a prompt to generate the hint
    # prompt = f"""
    # [INST] <<SYS>>
    # You are helping a student with the following problem. Provide guidance based on the problem description, their code, the console output, and the failed test case.
    # <</SYS>>

    # Problem Description: {problem_description}

    # Their Code:
    # {user_code}

    # The console output from running the code:
    # {code_output}

    # A failing test case takes the following input:
    # {failed_input}
    # Expects this output:
    # {failed_expected}
    # But got this output:
    # {failed_result}

    # Based on the problem description, their code, the console output, and the failed test case, provide a helpful hint on what might be wrong with their implementation and how they can improve it. [/INST]
    # """
    messages = [
        {
            "role": "system",
            "content": """
            You are an assistant helping users debug their FizzBuzz code. Your role is to guide them through debugging by asking questions and providing hints rather than offering full solutions. The task is to write a function that returns 'Fizz' for multiples of 3, 'Buzz' for multiples of 5, and 'FizzBuzz' for multiples of both. Help the user think through their mistakes by pointing out specific problems or potential improvements, but never provide the exact correct code. Instead, give step-by-step reasoning that leads the user to solve the problem on their own.
            """
        },
        {
            "role": "user",
            "content": f"""
            This is my code for FizzBuzz, but it doesn't seem to work. Can you help me identify what might be wrong without giving the full solution? What should I think about?:
            {user_code}
            """
        },
        {
            "role": "assistant",
            "content": """
            Here's how you should assist the user:

            - **First hint**: "Does the order of your conditions matter in this case?"
            - **Second hint**: "How could you structure your conditions to avoid checking for one value before checking for both?"
            - **Third hint**: "Would rearranging the conditions prevent unreachable code?"

            Problem Description: Write a function that returns 'Fizz' for multiples of 3, 'Buzz' for multiples of 5, and 'FizzBuzz' for multiples of both. Based on this description, ask guiding questions to help the user improve their logic rather than providing the full answer.
            """
        }
    ]



    print(messages)

    # Generate the hint using the LLM
    hint = llm.create_chat_completion(messages)

    print(hint)

    return {"hint": hint}