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
import faiss
import numpy as np
from transformers import AutoModel, AutoTokenizer
import torch
# Add route to generate a hint using the pre-loaded Llama model
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
import asyncio

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
    solution_code = Column(String)  # New field for the solution code
    solution_explanation = Column(String)  # New field for the solution explanation


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

from fastapi import FastAPI
from contextlib import asynccontextmanager
import faiss
import os
import json
from transformers import AutoTokenizer, AutoModel

@asynccontextmanager
async def lifespan(app: FastAPI):
    os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
    # Attach the raw checkpoint directly
    app.tokenizer = AutoTokenizer.from_pretrained("Salesforce/codet5p-110m-embedding", trust_remote_code=True)
    app.model = AutoModel.from_pretrained("Salesforce/codet5p-110m-embedding", trust_remote_code=True).to("cpu")

    # Dictionary of FAISS indices (one per problem_id)
    app.faiss_indices = {}
    app.embeddings_data = {}

    # Load or initialize FAISS indices and embeddings data for each problem
    for problem_id in range(1, 3):  # Adjust according to the range of your problem IDs
        index_path = f"faiss_index_{problem_id}.idx"
        data_path = f"embeddings_data_{problem_id}.json"
        
        if os.path.exists(index_path):
            app.faiss_indices[problem_id] = faiss.read_index(index_path)
        else:
            app.faiss_indices[problem_id] = faiss.IndexFlatL2(256)  # Assume 256-dimensional embeddings

        if os.path.exists(data_path):
            with open(data_path, 'r') as f:
                app.embeddings_data[problem_id] = json.load(f)
        else:
            app.embeddings_data[problem_id] = []

    yield

    # Save FAISS indices and embedding data after the app finishes
    for problem_id, faiss_index in app.faiss_indices.items():
        faiss.write_index(faiss_index, f"faiss_index_{problem_id}.idx")
        with open(f"embeddings_data_{problem_id}.json", 'w') as f:
            json.dump(app.embeddings_data[problem_id], f)

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
    return [{"id": p.id, "title": p.title, "description": p.description, "arguments": p.arguments, "solution_code": p.solution_code, "solution_explanation": p.solution_explanation} for p in problems]

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
        "solution_code": problem.solution_code,  # Include the solution code
        "solution_explanation": problem.solution_explanation,  # Include the solution explanation
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
    import pyperclip
    pyperclip.copy(request.code.replace('\n', '\\n').replace('"', "'"))
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


def stream_response(request):
    db = SessionLocal()
    
    # Fetch the problem description from the database
    problem = db.query(Problem).filter(Problem.id == request.problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    print(vars(problem))
    user_code = request.code
    correct_code = problem.solution_code.encode('utf-8').decode('unicode_escape')


    # First message to describe what the user's code is doing
    explanation_messages = [
        {
            "role": "system",
            "content": f"""
            You are an assistant that helps users debug their code by identifying logical issues. 
            Your goal is to explain exactly what the user's code is doing, step by step.
            The problem they are solving is:
            {problem.description}
            IMPORTANT: DO NOT DO ANYTHING MORE THAN BREAKING DOWN THE USER'S CODE, DO NOT EXPLAIN THE PROBLEM AGAIN TO ME, DO NOT PROPOSE IMPROVEMENTS.
            """
        },
        {
            "role": "user",
            "content": f"""
            This is my code for {problem.title}, but it doesn't seem to work. Describe exactly what 
            the code is doing, without giving the correct solution. JUST EXPLAIN WHAT THE CODE IS DOING STEP BY STEP NOW
            {user_code}
            IMPORTANT: DO NOT DO ANYTHING MORE THAN BREAKING DOWN THE USER'S CODE. ONCE YOU HAVE DESCRIBED WHAT THE CODE DOES STOP!
            """
        }
    ]

    code_llm = Llama(
        model_path="C:/Users/chowd/ProgrammingProjects/AlgoEasy/backend/Code-Llama-3-8B-Q8_0.gguf",
        f16_kv=True,
        verbose=True,
        chat_format="chatml",
        n_ctx=768,
        n_gpu_layers=10,
    )

    explanation = ""

    # Stream explanation from the LLM
    for stream_response in code_llm.create_chat_completion(explanation_messages, temperature=0.1, stream=True):
        if 'content' in stream_response["choices"][0]["delta"]:
            explanation_part = stream_response["choices"][0]["delta"]['content']
            explanation += explanation_part
            print(explanation, end="", flush=True)
            yield "data: " + explanation_part + "\n\n"

    # Send a message indicating that we are moving to similarity search
    yield "\n¶¶¶ Similarity search starting ¶¶¶\n"

    # Call find_similar internally
    similarity_request = SimilarityRequest(code=request.code, problem_id=request.problem_id)
    similarity_result = find_similar(similarity_request)

    mistake = None

    print(similarity_result)
    # Check similarity result and possibly set a mistake
    if similarity_result["similarity_score"] < 0.2:
        mistake = similarity_result["bug_description"]
        print("Going with the mistake")

    yield f"\nMost similar problem bug description: {similarity_result['bug_description']}, similarity score: {similarity_result['similarity_score']}\n"

    # Send another separator for transitioning to the hint section
    yield "\n¶¶¶ Hint generation starting ¶¶¶\n"

    # Create messages for hint generation
    raw_hint_messages = [
        {
            "role": "system",
            "content": f"""
            You are an assistant that helps users debug their code by identifying logical issues. 
            Your role is to point out logical errors and provide hints. Do not provide full solutions,
            but guide the user to the solution. The problem they are solving is:
            {problem.description}
            IMPORTANT: DO NOT PROVIDE A FULL SOLUTION!
            """
        },
        {
            "role": "user",
            "content": f"""
            This is my code for {problem.title}, but it doesn't seem to work. Can you describe exactly what 
            the code is doing, without giving the correct solution?:
            {user_code}

            Based on this explanation, here's what you said:
            {explanation}

            This is the correct code:
            {correct_code}

            EXPLANATION OF THE CORRECT CODE USE THIS TO GUIDE YOUR RESPONSE, BY CONTRASTING IT WITH THE USER CODE:
            {problem.solution_explanation}

            Now, can you help me identify what might be wrong? 
            What should I think about to correct the issue? Keep the correct code explanation in mind.
            IMPORTANT: DON'T PROVIDE THE FULL CODE

            INSTRUCTION: Now provide a brief hint, without giving everything away. AND DO NOT PROVIDE THE FULL SOLUTION OR ASK ME TO TEST CERTAIN CASES.
            """
        }
    ]

    hint_messages = raw_hint_messages if mistake is None else [
        {
            "role": "system",
            "content": f"""
            You are an assistant that helps users debug their code by identifying logical issues. 
            Your role is to point out logical errors and provide hints. Do not provide full solutions,
            but guide the user to the solution. We have an idea of where the user is going wrong. The problem they are solving is:
            {problem.description}
            IMPORTANT: DO NOT PROVIDE A FULL SOLUTION!
            """
        },
        {
            "role": "user",
            "content": f"""
            This is my code for {problem.title}, but it doesn't seem to work. Can you describe exactly what 
            the code is doing, without giving the correct solution?:
            {user_code}

            Based on this explanation, here's what you said:
            {explanation}

            This is the pitfall I could be falling into is:
            {mistake}

            Now, can you help me identify what might be wrong in my code? 
            What should I think about to correct the issue? Keep the pitfall above in mind.
            IMPORTANT: DON'T PROVIDE THE FULL CODE

            INSTRUCTION: Now provide a brief hint, without giving everything away. AND DO NOT PROVIDE THE FULL SOLUTION OR ASK ME TO TEST CERTAIN CASES.
            """
        }
    ]

    # Stream hint generation from the LLM
    for stream_response in code_llm.create_chat_completion(hint_messages, stream=True):
        if 'content' in stream_response["choices"][0]["delta"]:
            hint = stream_response["choices"][0]["delta"]['content']
            print(hint, end="", flush=True)
            yield "data: " + hint + "\n\n"

    del code_llm

@app.post("/generate_hint/")
async def generate_hint(request: CodeExecutionRequest):
    # Return a streaming response
    return StreamingResponse(stream_response(request), media_type="text/event-stream")


# Request model for embedding input
class EmbeddingRequest(BaseModel):
    problem_id: int
    code: str
    bug_description: str

@app.post("/add_embedding/")
async def add_embedding(request: EmbeddingRequest):
    inputs = app.tokenizer.encode(request.code, return_tensors="pt").cpu()
    with torch.no_grad():
        embedding = app.model(inputs)[0].cpu().numpy()

    if len(embedding.shape) == 1:
        embedding = embedding.reshape(1, -1)

    # Add the embedding to the FAISS index for the specific problem
    faiss_index = app.faiss_indices[request.problem_id]
    faiss_index.add(embedding.astype('float32'))

    # Store embedding details for the specific problem
    app.embeddings_data[request.problem_id].append({
        "problem_id": request.problem_id,
        "bug_description": request.bug_description
    })

    return {"message": "Embedding added successfully"}

class SimilarityRequest(BaseModel):
    code: str
    problem_id: int

@app.post("/find_similar/")
def find_similar(request: SimilarityRequest):
    inputs = app.tokenizer.encode(request.code, return_tensors="pt").cpu()
    
    with torch.no_grad():
        embedding = app.model(inputs)[0].cpu().numpy()

    if len(embedding.shape) == 1:
        embedding = embedding.reshape(1, -1)

    # Search the FAISS index corresponding to the problem ID
    faiss_index = app.faiss_indices[request.problem_id]
    D, I = faiss_index.search(embedding.astype('float32'), 1)

    closest_index = I[0][0]
    distance = float(D[0][0])  # Convert numpy.float32 to regular float

    # Retrieve the corresponding bug description
    bug_description = app.embeddings_data[request.problem_id][closest_index]["bug_description"]

    data = {
        "most_similar_problem_id": request.problem_id,
        "bug_description": bug_description,
        "similarity_score": distance  # Now a Python float
    }

    return data
