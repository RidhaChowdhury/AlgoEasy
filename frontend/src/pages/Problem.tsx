import { useLocation } from "react-router-dom";
import { useRef, useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import axios from "axios";
import { PlayCircle, ReceiptText, CircleSlash } from "lucide-react"; // Importing icons
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import { ScrollArea } from "@/components/ui/scroll-area";
import CodeMirror from "@uiw/react-codemirror";
import { python } from "@codemirror/lang-python";
import { sublime } from "@uiw/codemirror-themes-all";
import { Separator } from "@/components/ui/separator";

// Define the Problem type
type Problem = {
  id: number;
  title: string;
  description: string;
  arguments: string; // Arguments for the solution function
};

// Define the structure for test case data
type TestCase = {
  inputs: string[];
  expected_output: string;
};

const Problem = () => {
  const editorRef = useRef<any>(null);

  const location = useLocation();
  const { problem } = location.state || {}; // Get the problem data from location state

  const [code, setCode] = useState(
    problem ? `def solution(${problem.arguments}):\n    pass\n` : ""
  );
  const [testCases, setTestCases] = useState<TestCase[]>([]);
  const [selectedTestCaseIndex, setSelectedTestCaseIndex] = useState<number>(0);
  const [loadingTestCases, setLoadingTestCases] = useState<boolean>(true);
  const [executionResults, setExecutionResults] = useState<any[]>([]);

  useEffect(() => {
    if (problem) {
      setCode(`def solution(${problem.arguments}):\n    pass\n`);
      fetchTestCases(problem.id);
    }
  }, [problem]);

  // Fetch test cases for the selected problem
  const fetchTestCases = async (problemId: number) => {
    try {
      const response = await axios.get(
        `http://localhost:8000/problems/${problemId}/test_cases`
      );
      setTestCases(response.data);
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
          problem_id: problem.id,
        });
        const result = response.data;

        // Handle test cases and console output from the execution
        if (result.test_cases) {
          setExecutionResults(result.test_cases);
        }
      } catch (error) {
        console.error("Error during code execution:", error);
      }
    }
  };

  // Get console output (stdout and stderr) for the selected test case
  const getConsoleOutputForTestCase = (testCaseIndex: number) => {
    const selectedResult = executionResults[testCaseIndex];
    if (!selectedResult) {
      return ["No output."];
    }
    return [
      ...selectedResult.stdout.map((line: any) =>
        typeof line === "string"
          ? { type: "log", message: line }
          : { type: "error", message: "Invalid output" }
      ),
      ...selectedResult.stderr.map((line: any) =>
        typeof line === "string"
          ? { type: "error", message: line }
          : { type: "error", message: "Invalid error output" }
      ),
    ];
  };

  // Get button background color based on test case result
  const getTestCaseButtonColor = (index: number) => {
    if (!executionResults.length) return "bg-gray-700"; // Not run yet
    const result = executionResults[index]?.test_result?.passed;
    if (result === true) return "bg-green-600";
    if (result === false) return "bg-red-600";
    return "bg-gray-700"; // Not run yet
  };

  return (
    <div className="h-screen w-screen flex flex-col bg-[#303940] text-[#d4d4d4]">
      <ResizablePanelGroup direction="horizontal" className="flex-1">
        {/* Left Panel: Problem Description */}
        <ResizablePanel
          defaultSize={25}
          className="bg-[#303940] text-[#d4d4d4]"
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
          className="bg-[#303940] text-[#d4d4d4]"
        >
          <ResizablePanelGroup direction="vertical" className="h-full">
            {/* Top Right: Editor with Play button */}
            <ResizablePanel
              defaultSize={60}
              className="bg-[#303940] flex flex-col relative"
            >
              <div className="flex flex-col h-full">
                {/* CodeMirror Editor */}
                <div className="flex-1 overflow-hidden">
                  <CodeMirror
                    value={code}
                    height="100%"
                    extensions={[python()]}
                    theme={sublime}
                    onChange={(value: string) => setCode(value)}
                    className="h-full"
                  />
                </div>
                {/* Play Button Overlay */}
                <div className="absolute top-2 right-4 z-10">
                  <Button onClick={executeCode} className="bg-[#007acc] p-2">
                    <PlayCircle className="w-6 h-6 text-white" />
                  </Button>
                </div>
              </div>
            </ResizablePanel>
            <ResizableHandle />

            {/* Bottom Section with 3 Resizable Panels */}
            <ResizablePanel defaultSize={40} className="bg-[#1E252A]">
              <ResizablePanelGroup direction="horizontal" className="h-full">
                {/* Left Panel: Test Case Selection */}
                <ResizablePanel defaultSize={10} maxSize={10} minSize={10} className="h-full">
                  <ScrollArea className="h-full">
                    <div className="p-2 text-center">
                      <h3 className="text-lg font-semibold">Cases</h3>
                      <ul>
                        {testCases.map((testCase, index) => (
                          <li key={index}>
                            <button
                              className={`block w-full text-center p-2 mb-2 ${getTestCaseButtonColor(
                                index
                              )}`}
                              onClick={() => setSelectedTestCaseIndex(index)}
                            >
                              #{index + 1}
                            </button>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </ScrollArea>
                </ResizablePanel>
                <ResizableHandle />

                {/* Middle Panel: Test Case Details */}
                <ResizablePanel defaultSize={40} className="h-full">
                  <div className="p-4">
                    <h3 className="text-lg font-semibold">Test Case Details</h3>
                    {testCases[selectedTestCaseIndex] && (
                      <div>
                        <strong>Inputs:</strong>{" "}
                        {JSON.stringify(
                          testCases[selectedTestCaseIndex].inputs
                        )}
                        <br />
                        <strong>Expected Output:</strong>{" "}
                        {testCases[selectedTestCaseIndex].expected_output}
                        <br />
                        {executionResults.length > 0 && (
                          <>
                            <strong>Actual Output:</strong>{" "}
                            {
                              executionResults[selectedTestCaseIndex]
                                ?.test_result?.result
                            }
                            <br />
                            <strong>Passed:</strong>{" "}
                            {executionResults[selectedTestCaseIndex]
                              ?.test_result?.passed
                              ? "✅"
                              : "❌"}
                          </>
                        )}
                      </div>
                    )}
                  </div>
                </ResizablePanel>
                <ResizableHandle />

                {/* Right Panel: Console Output */}
                <ResizablePanel defaultSize={40} className="h-full">
                  <ScrollArea className="h-full p-4">
                    <h3 className="text-lg font-semibold">Console Output</h3>
                    <div className="text-sm">
                      {executionResults.length > 0 ? (
                        getConsoleOutputForTestCase(selectedTestCaseIndex).map(
                          (log, index) => (
                            <>
                              <div
                                key={index}
                                className="flex items-center space-x-2"
                                >
                                {log.type === "error" ? (
                                  <CircleSlash className="text-red-500" />
                                ) : (
                                  <ReceiptText className="text-white" />
                                )}
                                <span
                                  className={
                                    log.type === "error" ? "text-red-500" : ""
                                  }
                                  >
                                  {log.message}
                                </span>
                              </div>
                              <Separator className="m-2"/>
                            </>
                          )
                        )
                      ) : (
                        <p>No output.</p>
                      )}
                    </div>
                  </ScrollArea>
                </ResizablePanel>
              </ResizablePanelGroup>
            </ResizablePanel>
          </ResizablePanelGroup>
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  );
};

export default Problem;
