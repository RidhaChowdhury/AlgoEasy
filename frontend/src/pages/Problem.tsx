import { useLocation } from "react-router-dom";
import { useRef, useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import axios from "axios";

const Problem = () => {
  const editorRef = useRef<
    import("monaco-editor").editor.IStandaloneCodeEditor | null
  >(null);
  const [code, setCode] = useState(`# This is Python code
def solution(n):
    if n % 3 == 0 and n % 5 == 0:
        return "FizzBuzz"
    elif n % 3 == 0:
        return "Fizz"
    elif n % 5 == 0:
        return "Buzz"
    else:
        return str(n)
`);

  const [testResults, setTestResults] = useState<any[]>([]);

  const handleEditorDidMount = (
    editor: import("monaco-editor").editor.IStandaloneCodeEditor
  ) => {
    editorRef.current = editor;
  };

  const executeCode = async () => {
  // Function to print the code from the editor to the console
  const printCode = () => {
    if (editorRef.current) {
      const currentCode = editorRef.current.getValue();

      try {
        const response = await axios.post("http://localhost:8000/execute/", {
          code: currentCode,
        });

        const result = response.data;
        console.log("Execution result:", result);

        if (result.test_cases) {
          setTestResults(result.test_cases);
        }

        // Log stdout
        if (result.stdout && result.stdout.length > 0) {
          result.stdout.forEach((output: any) => {
            console.log(`[${output.timestamp}] ${output.output}`);
          });
        }

        // Log stderr
        if (result.stderr && result.stderr.length > 0) {
          result.stderr.forEach((error: any) => {
            console.error(`[${error.timestamp}] ${error.error}`);
          });
        }
      } catch (error) {
        console.error("Error during code execution:", error);
      }
      console.log("Current code in editor:", currentCode);
    } else {
      console.error("Test cases are still loading");
    }
  };

  return (
    <div className="h-screen w-screen flex flex-col">
      <h1 className="text-center py-4 bg-gray-800 text-white">
        Monaco Code Editor for Python
      </h1>
      <Editor
        height="80vh"
        width="100vw"
        language="python"
        theme="vs-dark"
        value={code}
        onMount={handleEditorDidMount}
        onChange={(newValue: string | undefined) => setCode(newValue || "")}
        options={{
          automaticLayout: true,
          fontSize: 14,
          scrollBeyondLastLine: false,
        }}
      />
      <div className="flex justify-center mt-4">
        <Button onClick={printCode}>Print Code to Console</Button>{" "}
      </div>
      <div className="mt-8 px-8">
        <h2 className="text-lg font-semibold">Test Case Results:</h2>
        <ul>
          {testResults.map((result, index) => (
            <li key={index} className="my-2">
              <div>
                <strong>Inputs:</strong> {JSON.stringify(result.inputs)}
              </div>
              <div>
                <strong>Expected:</strong> {result.expected}
              </div>
              <div>
                <strong>Result:</strong> {result.result}
              </div>
              <div>
                <strong>Passed:</strong> {result.passed ? "✅" : "❌"}
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};

export default Problem;