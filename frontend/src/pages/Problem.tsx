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

  // Function to print the code from the editor to the console
  const printCode = () => {
    if (editorRef.current) {
      const currentCode = editorRef.current.getValue();
      console.log("Current code in editor:", currentCode);
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
        <Button onClick={printCode}>Print Code to Console</Button>{" "}
      </div>
    </div>
  );
};

export default Problem;
