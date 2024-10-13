import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"; // Import ShadCN Table components
import { BrainCircuit } from "lucide-react";

// Define the Problem type
type Problem = {
  id: number;
  title: string;
  description: string;
  arguments: string;
};

const ProblemSelection = () => {
  const navigate = useNavigate();
  const [problems, setProblems] = useState<Problem[]>([]); // State to store fetched problems
  const [loading, setLoading] = useState(true); // Loading state

  // Function to fetch problems from the backend
  const fetchProblems = async () => {
    try {
      const response = await axios.get("http://localhost:8000/problems"); // Replace with your actual backend URL
      const sortedProblems = response.data.sort(
        (a: Problem, b: Problem) => a.id - b.id
      ); // Sort by ID
      setProblems(sortedProblems);
    } catch (error) {
      console.error("Error fetching problems:", error);
    } finally {
      setLoading(false);
    }
  };

  // Fetch problems when the component mounts
  useEffect(() => {
    fetchProblems();
  }, []);

  // Function to handle when a problem is selected
  const handleProblemSelect = (problem: Problem) => {
    navigate(`/problem/${problem.id}`, { state: { problem } });
  };

  // Render Skeleton while loading
  if (loading) {
    return (
      <div className="h-screen w-screen flex flex-col bg-[#1e1e1e] text-white p-4">
        <h2 className="text-xl font-semibold mb-4">Select a Problem</h2>
        <ul>
          {/* Render multiple skeleton items for the loading state */}
          {Array(5)
            .fill(0)
            .map((_, idx) => (
              <li key={idx} className="mb-2">
                <div className="flex items-center space-x-4">
                  <Skeleton className="h-12 w-12 rounded-full" />
                  <div className="space-y-2">
                    <Skeleton className="h-4 w-[250px]" />
                    <Skeleton className="h-4 w-[200px]" />
                  </div>
                </div>
              </li>
            ))}
        </ul>
      </div>
    );
  }

  // Render the list of problems in a table
  return (
    <div className="h-screen w-screen flex flex-col bg-[#303940] text-white p-4">
      <div className="flex flex-row text-align-center">
        <BrainCircuit className="mr-2 text-blue-500" />
        <h1 className="text-xl font-semibold mb-4">
          <span className="text-blue-500">Algo</span>Easy
        </h1>
      </div>

      <Table>
        <TableCaption>A list of available problems.</TableCaption>
        <TableHeader>
          <TableRow>
            <TableHead className="w-[50px]">#</TableHead> {/* Problem ID */}
            <TableHead>Title</TableHead>
            <TableHead>Description</TableHead> {/* First 50 characters */}
          </TableRow>
        </TableHeader>
        <TableBody>
          {problems.map((problem: Problem) => (
            <TableRow
              key={problem.id}
              onClick={() => handleProblemSelect(problem)} // Handle row click
              className="cursor-pointer hover:bg-[#2a2a2a]" // Add hover effect for table rows
            >
              <TableCell className="font-medium">{problem.id}</TableCell>
              <TableCell>{problem.title}</TableCell>
              <TableCell>{problem.description.substring(0, 100)}...</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
};

export default ProblemSelection;
