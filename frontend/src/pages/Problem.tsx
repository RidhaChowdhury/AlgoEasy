import { useLocation } from "react-router-dom";
import { useRef, useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import axios from "axios";
import { PlayCircle } from "lucide-react";
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import CodeMirror from "@uiw/react-codemirror";
import { python } from "@codemirror/lang-python";
import { sublime } from "@uiw/codemirror-themes-all";

// Define the Problem type
type Problem = {
  id: number;
  title: string;
  description: string;
  arguments: string; // Arguments for the solution function
};

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
    </div>
  );
};

export default Problem;