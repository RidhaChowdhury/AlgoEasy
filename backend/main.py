from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import subprocess
import time
import re

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

@app.get("/")
def read_root():
    return {"message": "Backend is responding!"}

@app.post("/execute/")
def execute_code(request: CodeExecutionRequest):
    # Save the code to a temporary file
    temp_code_file = "temp_code.py"
    with open(temp_code_file, "w") as f:
        f.write(request.code)

    # Run the code with subprocess and capture output and errors
    try:
        process = subprocess.Popen(
            ["python", temp_code_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Capture stdout and stderr
        stdout, stderr = process.communicate()

        # Update the timestamp to only show time (HH:MM:SS)
        result = {
            "stdout": [],
            "stderr": [],
        }

        # Split and tag each line of stdout
        if stdout:
            for line in stdout.splitlines():
                result["stdout"].append({
                    "timestamp": time.strftime("%H:%M:%S", time.localtime()),  # Time only
                    "output": line
                })

        # Process stderr to group multiple errors separately
        if stderr:
            # Split the stderr by the "Traceback" keyword to capture separate error blocks
            error_blocks = re.split(r'(Traceback \(most recent call last\):)', stderr)
            grouped_errors = []
            
            # Iterate through the blocks and combine traceback with following lines
            for i in range(1, len(error_blocks), 2):
                traceback_start = error_blocks[i].strip()
                traceback_content = error_blocks[i + 1].strip() if i + 1 < len(error_blocks) else ""
                full_error = traceback_start + "\n" + traceback_content
                grouped_errors.append(full_error)

            # Add each error block with a timestamp
            for error in grouped_errors:
                result["stderr"].append({
                    "timestamp": time.strftime("%H:%M:%S", time.localtime()),  # Time only
                    "error": error.strip()  # Aggregate the entire error block
                })

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
