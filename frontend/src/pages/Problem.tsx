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
  const editorRef = useRef<any>(null);

  const location = useLocation();
  const { problem } = location.state || {}; // Get the problem data from location state

  // Dynamically generate the initial code using the problem's arguments
  const generateInitialCode = (args: string) =>
    `def solution(${args}):\n    pass\n`;

  const [code, setCode] = useState(
    problem
      ? generateInitialCode(problem.arguments)
      : "def solution():\n    pass\n"
  );
  const [testResults, setTestResults] = useState<any[]>([]);
  const [consoleOutput, setConsoleOutput] = useState<any[]>([]);
  const [loadingTestCases, setLoadingTestCases] = useState<boolean>(true);

  useEffect(() => {
    if (problem) {
      setCode(generateInitialCode(problem.arguments)); // Reset code to initial code when problem changes

      // Fetch the test cases for the selected problem
      fetchTestCases(problem.id);
    }
  }, [problem]);

  const fetchTestCases = async (problemId: number) => {
    try {
      const response = await axios.get(
        `http://localhost:8000/problems/${problemId}/test_cases`
      );
      setTestResults(response.data); // Store the test cases for later use
      setLoadingTestCases(false);
    } catch (error) {
      console.error("Error fetching test cases:", error);
      setLoadingTestCases(false);
    }
  };

  const executeCode = async () => {
    if (!loadingTestCases) {
      try {
        const response = await axios.post("http://localhost:8000/execute/", {
          code: code,
          problem_id: problem.id, // Pass the problem ID
        });

        const result = response.data;

        // Handle test cases
        if (result.test_cases) {
          setTestResults(result.test_cases);
        }

        // Handle console output
        const consoleLogs: any[] = [];
        if (result.stdout && result.stdout.length > 0) {
          result.stdout.forEach(([timestamp, output]: [string, string]) => {
            consoleLogs.push(`[${timestamp}] ${output}`);
          });
        }

        if (result.stderr && result.stderr.length > 0) {
          result.stderr.forEach((error: any) => {
            consoleLogs.push(`[${error.timestamp}] ${error.error}`);
          });
        }

        setConsoleOutput(consoleLogs);
      } catch (error) {
        console.error("Error during code execution:", error);
      }
    } else {
      console.error("Test cases are still loading");
    }
  };

  return (
    <div className="h-screen w-screen flex flex-col bg-[#303940] text-[#d4d4d4]">
      <ResizablePanelGroup direction="horizontal" className="flex-1">
        {/* Left Panel: Problem Description */}
        <ResizablePanel
          defaultSize={25}
          className="bg-[#303940] text-[#d4d4d4] h-full"
        >
          <div className="h-full p-4">
            <h2 className="text-xl font-semibold mb-4">
              {problem?.title || "Problem"}
            </h2>
            <p>{problem?.description || "Select a problem from the list."}</p>
          </div>
        </ResizablePanel>
        <ResizableHandle />
        {/* Right Panel: Editor and Test Results */}
        <ResizablePanel
          defaultSize={75}
          className="bg-[#303940] text-[#d4d4d4] h-full flex flex-col"
        >
          <ResizablePanelGroup direction="vertical" className="flex-1">
            {/* Top Right: Editor with header */}
            <ResizablePanel
              defaultSize={60}
              className="bg-[#303940] flex flex-col relative" // Add relative positioning
            >
              <div className="flex flex-col h-full">
                {/* CodeMirror Editor */}
                <CodeMirror
                  value={code}
                  height="100%"
                  extensions={[python()]}
                  theme={sublime}
                  onChange={(value: string) => setCode(value)}
                  style={{ overflowY: "auto", height: "100%" }}
                  basicSetup={{
                    lineNumbers: true,
                    autocompletion: true,
                  }}
                />
                {/* Play Button Overlay */}
                <div className="absolute top-2 right-4 z-10">
                  <Button onClick={executeCode} className="bg-[#007acc] p-2">
                    <PlayCircle className="w-6 h-6 text-white" />
                  </Button>
                </div>
              </div>
            </ResizablePanel>
            <ResizableHandle />
            {/* Bottom Bar: Tabs with Test Case Results and Console Output */}
            <ResizablePanel
              defaultSize={40}
              className="bg-[#303940] text-[#d4d4d4] flex-grow"
            >
              <Tabs defaultValue="testCases" className="h-full">
                <TabsList className="m-2 bg-[#3c474f] rounded-lg">
                  <TabsTrigger
                    value="testCases"
                    className="px-4 py-2 rounded-md text-gray-300 transition-all duration-200 ease-in-out
      data-[state=active]:bg-[#1E252A] data-[state=active]:text-white
      data-[state=inactive]:bg-transparent data-[state=inactive]:text-gray-400"
                  >
                    Test Cases
                  </TabsTrigger>
                  <TabsTrigger
                    value="console"
                    className="px-4 py-2 rounded-md text-gray-300 transition-all duration-200 ease-in-out
      data-[state=active]:bg-[#1E252A] data-[state=active]:text-white
      data-[state=inactive]:bg-transparent data-[state=inactive]:text-gray-400"
                  >
                    Console Output
                  </TabsTrigger>
                </TabsList>
                {/* Test Case Results Tab */}
                <TabsContent value="testCases" className="h-full flex-grow">
                  <ScrollArea className="h-full w-full overflow-y-auto ml-2">
                    <div className="pb-14">
                      {testResults.length > 0 ? (
                        testResults.map((result, index) => (
                          <div key={index} className="mb-2">
                            <div>
                              <strong>Inputs:</strong>{" "}
                              {JSON.stringify(result.inputs)}
                            </div>
                            <div>
                              <strong>Expected:</strong> {result.expected}
                            </div>
                            <div>
                              <strong>Result:</strong> {result.result}
                            </div>
                            <div>
                              <strong>Passed:</strong>{" "}
                              {result.passed ? "✅" : "❌"}
                            </div>
                            {index < testResults.length - 1 && (
                              <Separator className="my-2 bg-[#333333]" />
                            )}
                          </div>
                        ))
                      ) : (
                        <p>No test cases available.</p>
                      )}
                    </div>
                  </ScrollArea>
                </TabsContent>
                {/* Console Output Tab */}
                <TabsContent value="console" className="h-full flex-grow">
                  <ScrollArea className="h-full w-full overflow-y-auto m-2">
                    <div className="pb-14">
                      {consoleOutput.length > 0 ? (
                        consoleOutput.map((line, index) => (
                          <div key={index} className="mb-2">
                            {line}
                          </div>
                        ))
                      ) : (
                        <p>No output.</p>
                      )}
                    </div>
                  </ScrollArea>
                </TabsContent>
              </Tabs>
            </ResizablePanel>
          </ResizablePanelGroup>
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  );
};

export default Problem;