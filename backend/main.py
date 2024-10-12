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

        # Handle stdout (test results)
        if stdout:
            test_results = json.loads(stdout.strip())
            result["test_cases"] = test_results

        # Handle stderr (errors during execution)
        if stderr:
            for line in stderr.splitlines():
                result["stderr"].append({
                    "timestamp": time.strftime("%H:%M:%S", time.localtime()),
                    "error": line
                })

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Clean up the temporary user code file
        if os.path.exists(temp_code_file):
            os.remove(temp_code_file)
