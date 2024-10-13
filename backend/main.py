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

# Set up FastAPI with lifespan
app = FastAPI()

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

    # # Execute the code to get output
    # execute_response = execute_code(request)
    
    # failing_test_case = None
    # # Get the first test case's results from the execution response
    # for case in execute_response['test_cases']:
    #     print(case)
    #     if case['test_result']['passed'] == False:
    #         failing_test_case = case

    # if not failing_test_case:
    #     raise HTTPException(status_code=500, detail="No test case results found")

    # # Extract stdout and stderr from the first test case
    # stdout = failing_test_case.get('stdout', [])
    # stderr = failing_test_case.get('stderr', [])

    # # Combine the problem description, user code, and the first test case's output
    # problem_description = problem.description
    # code_output = "\n".join(stdout + stderr)
    user_code = request.code

    # # Add test case data
    # failed_input = str(failing_test_case['test_result']['inputs'])
    # failed_expected = str(failing_test_case['test_result']['expected'])
    # failed_result = str(failing_test_case['test_result']['result'])

    # Access the pre-loaded Llama model from the app state

    problem_description = """
    Write a function that returns 'Fizz' for multiples of 3, 'Buzz' for multiples of 5, 
    and 'FizzBuzz' for multiples of both 3 and 5. If a number is not divisible by either, 
    return the number itself as a string.
    """

    correct_code = """
    def solution(n: int):
        if n % 3 == 0 and n % 5 == 0:
            return "FizzBuzz"
        elif n % 3 == 0:
            return "Fizz"
        elif n % 5 == 0:
            return "Buzz"
        else:
            return str(n)
    """

    correct_code_explanation = """
    The correct FizzBuzz solution works as follows:
    1. The first condition checks if the number is divisible by both 3 and 5 (using `n % 3 == 0 and n % 5 == 0`). This catches numbers like 15, 30, etc., returning "FizzBuzz".
    2. The second condition checks if the number is divisible by only 3. If it is, it returns "Fizz".
    3. The third condition checks if the number is divisible by only 5. If it is, it returns "Buzz".
    4. If none of these conditions are met, the function returns the number itself as a string.
    The order of these conditions is crucial to avoid redundant checks and to ensure that "FizzBuzz" is checked first.
    """

    # First message to describe what the user's code is doing
    explanation_messages = [
        {
            "role": "system",
            "content": f"""
            You are an assistant that helps users debug their code by identifying logical issues. 
            Your goal is to explain exactly what the user's code is doing, step by step.
            The problem they are solving is:
            {problem_description}
            IMPORTANT: DO NOT DO ANYTHING MORE THAN BREAKING DOWN THE USER'S CODE, DO NOT EXPLAIN THE PROBLEM AGAIN TO THEM, DO NOT PROPOSE IMPROVEMENTS.
            """
        },
        {
            "role": "user",
            "content": f"""
            This is my code for FizzBuzz, but it doesn't seem to work. Describe exactly what 
            the code is doing, without giving the correct solution. JUST EXPLAIN WHAT THE CODE IS DOING STEP BY STEP NOW
            {user_code}
            IMPORTANT: DO NOT DO ANYTHING MORE THAN BREAKING DOWN THE USER'S CODE, DO NOT EXPLAIN THE PROBLEM AGAIN TO THEM, DO NOT PROPOSE IMPROVEMENTS.
            """
        }
    ]

    # Variable to store the explanation
    explanation = ""

    # Start the timer for the explanation
    import time
    start_time_explanation = time.time()

    code_llm = Llama(
        model_path="C:/Users/chowd/ProgrammingProjects/AlgoEasy/backend/Code-Llama-3-8B-Q8_0.gguf",
        f16_kv=True,  # MUST set to True to avoid issues after a few calls
        verbose=True,
        chat_format="chatml",
        n_ctx=1024,
        n_gpu_layers=20,
    )

    # Call the LLM to get the explanation and stream/aggregate the response
    print("### Explanation ###")
    for stream_response in code_llm.create_chat_completion(explanation_messages, temperature=0.1, stream=True):
        if 'content' in stream_response["choices"][0]["delta"]:
            # Aggregate the explanation into a variable and print as it's being streamed
            explanation_part = stream_response["choices"][0]["delta"]['content']
            print(explanation_part, end="", flush=True)
            explanation += explanation_part

    # End the timer for the explanation
    end_time_explanation = time.time()
    explanation_time = end_time_explanation - start_time_explanation
    print(f"\n\nExplanation generated in {explanation_time:.2f} seconds.")

    # Second message to provide a hint based on the explanation and the correct code
    hint_messages = [
        {
            "role": "system",
            "content": f"""
            You are an assistant that helps users debug their code by identifying logical issues. 
            Your role is to point out logical errors and provide hints. Do not provide full solutions,
            but guide the user to the solution. The problem they are solving is:
            {problem_description}
            IMPORTANT: DO NOT PROVIDE A FULL SOLUTION!
            """
        },
        {
            "role": "user",
            "content": f"""
            This is my code for FizzBuzz, but it doesn't seem to work. Can you describe exactly what 
            the code is doing, without giving the correct solution?:
            {user_code}

            Based on this explanation, here's what you said:
            {explanation}

            This is the correct code:
            {correct_code}

            EXPLANATION OF THE CORRECT CODE USE THIS TO GUIDE YOUR RESPONSE, BY CONTRASTING IT WITH THE USER CODE:
            {correct_code_explanation}

            Now, can you help me identify what might be wrong? 
            What should I think about to correct the issue? Keep the correct code explanation in mind.
            IMPORTANT: DON'T PROVIDE THE FULL CODE

            INSTRUCTION: Now provide a brief hint, without giving everything away. AND DO NOT PROVIDE THE FULL SOLUTION OR ASK THEM TO TEST CERTAIN CASES.
            """
        }
    ]

    # Start the timer for the hint
    start_time_hint = time.time()

    # Call the LLM to get the hint
    print("\n\n### Hint ###")
    for stream_response in code_llm.create_chat_completion(hint_messages, stream=True):
        if 'content' in stream_response["choices"][0]["delta"]:
            print(stream_response["choices"][0]["delta"]['content'], end="", flush=True)

    # End the timer for the hint
    end_time_hint = time.time()
    hint_time = end_time_hint - start_time_hint
    print(f"\n\nHint generated in {hint_time:.2f} seconds.")


    # return {"hint": hint}