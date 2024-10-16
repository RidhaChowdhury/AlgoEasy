import { useLocation } from "react-router-dom";
import { useRef, useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import axios from "axios";
import { fetchEventSource } from "@microsoft/fetch-event-source";
import {
  PlayCircle,
  ReceiptText,
  CircleSlash,
  BotMessageSquare,
  Brain,
  BrainCog
} from "lucide-react";
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
  arguments: string;
};

// Define the structure for test case data
type TestCase = {
  inputs: string[];
  expected_output: string;
};

const Problem = () => {
  const editorRef = useRef<any>(null);
  const location = useLocation();
  const { problem } = location.state || {};

  const [code, setCode] = useState(
    problem ? `def solution(${problem.arguments}):\n    pass\n` : ""
  );
  const [testCases, setTestCases] = useState<TestCase[]>([]);
  const [selectedTestCaseIndex, setSelectedTestCaseIndex] = useState<number>(0);
  const [loadingTestCases, setLoadingTestCases] = useState<boolean>(true);
  const [executionResults, setExecutionResults] = useState<any[]>([]);
  const [aiResponses, setAiResponses] = useState<string[]>([]);
  const [isLoadingHint, setIsLoadingHint] = useState<boolean>(false);
  const [wasSeen, setWasSeen] = useState<boolean>(false);

  useEffect(() => {
    if (problem) {
      setCode(`def solution(${problem.arguments}):\n    pass\n`);
      fetchTestCases(problem.id);
    }
  }, [problem]);

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
        if (result.test_cases) {
          setExecutionResults(result.test_cases);
        }
      } catch (error) {
        console.error("Error during code execution:", error);
      }
    }
  };

  const getHint = async () => {
    setIsLoadingHint(true);
    setWasSeen(false); // Reset wasSeen to false initially
    setAiResponses([]); // Reset the previous AI responses
    let completeResponse = ""; // To accumulate the full message

    // Call find_similar first
    try {
      const similarityRes = await fetch("http://localhost:8000/find_similar/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          code: code,
          problem_id: problem.id,
        }),
      });

      if (!similarityRes.ok) {
        console.error("Error calling find_similar:", similarityRes.statusText);
        throw new Error("Error calling find_similar");
      }

      const similarityData = await similarityRes.json();
      const similarityScore = similarityData.similarity_score;

      // If the similarity score is less than 0.1, set wasSeen to true
      if (similarityScore < 0.1) {
        setWasSeen(true);
      }

      // Proceed to call generate_hint if needed
      await fetchEventSource("http://localhost:8000/generate_hint/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "text/event-stream",
        },
        body: JSON.stringify({
          code: code,
          problem_id: problem.id,
        }),
        onopen: async (res) => {
          if (res.ok && res.status === 200) {
            console.log("Connection made ", res);
          } else if (
            res.status >= 400 &&
            res.status < 500 &&
            res.status !== 429
          ) {
            console.log("Client-side error ", res);
          }
        },
        onmessage(event) {
          const newResponse = event.data;
          completeResponse += newResponse; // Concatenate all parts
          setAiResponses([completeResponse]); // Set the concatenated string as a single response
        },
        onclose() {
          console.log("Connection closed by the server");
          setIsLoadingHint(false);
        },
        onerror(err) {
          console.log("There was an error from server", err);
          setIsLoadingHint(false);
          setAiResponses((prev) => [
            ...prev,
            "Error fetching hint. Please try again.",
          ]);
        },
      });
    } catch (error) {
      console.error("Error getting hint:", error);
      setAiResponses((prev) => [
        ...prev,
        "Error fetching hint. Please try again.",
      ]);
      setIsLoadingHint(false);
    }
  };


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

  const getTestCaseButtonColor = (index: number) => {
    if (!executionResults.length) return "bg-gray-700";
    const result = executionResults[index]?.test_result?.passed;
    if (result === true) return "bg-green-600";
    if (result === false) return "bg-red-600";
    return "bg-gray-700";
  };

  return (
    <div className="h-screen w-screen flex flex-col bg-[#303940] text-[#d4d4d4]">
      <ResizablePanelGroup direction="horizontal" className="flex-1">
        {/* Left Panel: Problem Description and AI Hint */}
        <ResizablePanel
          defaultSize={25}
          className="bg-[#303940] text-[#d4d4d4]"
        >
          <ResizablePanelGroup direction="vertical">
            {/* Problem Description */}
            <ResizablePanel defaultSize={50}>
              <div className="h-full p-4">
                <h2 className="text-xl font-semibold mb-4">
                  {problem?.title || "Problem"}
                </h2>
                <p>
                  {problem?.description || "Select a problem from the list."}
                </p>
              </div>
            </ResizablePanel>
            <ResizableHandle />
            {/* AI Hint Panel */}
            <ResizablePanel defaultSize={50}>
              <div className="h-full p-4 flex flex-col">
                <div className="flex flex-row w-full justify-between">
                  <h3 className="text-lg font-semibold mb-2">AI Hint</h3>
                  {!wasSeen ? <Brain/> : <BrainCog className="text-yellow-400"/>}
                </div>
                <ScrollArea className="flex-grow mb-4">
                  {aiResponses.map((response, index) => (
                    <div key={index} className="mb-2">
                      <p>{response}</p>
                      {index < aiResponses.length - 1 && (
                        <Separator className="my-2" />
                      )}
                    </div>
                  ))}
                </ScrollArea>
                <div className="">
                  <Button
                    onClick={getHint}
                    className="bg-[#547c97] p-2 w-full"
                    disabled={isLoadingHint}
                  >
                    <BotMessageSquare className="w-6 h-6 mr-2 text-white" />
                    {isLoadingHint ? "Getting hint..." : "I need a hint!"}
                  </Button>
                </div>
              </div>
            </ResizablePanel>
          </ResizablePanelGroup>
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
                <div className="absolute top-2 right-4 z-10 flex flex-row gap-2">
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
                <ResizablePanel
                  defaultSize={10}
                  maxSize={10}
                  minSize={10}
                  className="h-full"
                >
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
                            <div key={index}>
                              <div className="flex items-center space-x-2">
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
                              <Separator className="my-2 opacity-50" />
                            </div>
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
