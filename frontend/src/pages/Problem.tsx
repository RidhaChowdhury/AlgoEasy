import { useRef, useState } from "react";
import Editor from "@monaco-editor/react";
import { Button } from "@/components/ui/button";

const Problem = () => {
  const editorRef = useRef<
    import("monaco-editor").editor.IStandaloneCodeEditor | null
  >(null);
  const [code, setCode] = useState(`# This is Python code
def hello_world():
    print("Hello, world!")
    
hello_world()
`);

  // Function to handle when the editor is mounted
  const handleEditorDidMount = (
    editor: import("monaco-editor").editor.IStandaloneCodeEditor
  ) => {
    editorRef.current = editor;
    console.log("Editor is mounted and available:", editor);
  };

  // Function to execute the code by sending it to the FastAPI backend
  const executeCode = async () => {
    if (editorRef.current) {
      const currentCode = editorRef.current.getValue();

      try {
        // Send a POST request to the FastAPI backend
        const response = await fetch("http://localhost:8000/execute/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ code: currentCode }),
        });

        if (!response.ok) {
          throw new Error("Failed to execute the code.");
        }

        const result = await response.json();
        console.log("Execution result:", result);

        // Log both stdout and stderr to the console
        if (result.stdout && result.stdout.length > 0) {
          result.stdout.forEach((output: any) => {
            console.log(`[${output.timestamp}] ${output.output}`);
          });
        }

        if (result.stderr && result.stderr.length > 0) {
          result.stderr.forEach((error: any) => {
            console.error(`[${error.timestamp}] ${error.error}`);
          });
        }
      } catch (error) {
        console.error("Error during code execution:", error);
      }
    } else {
      console.error("Editor is not available");
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
        <Button onClick={executeCode}>Execute Code</Button>{" "}
      </div>
    </div>
  );
};

export default Problem;
