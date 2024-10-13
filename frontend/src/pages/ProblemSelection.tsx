import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { Skeleton } from "@/components/ui/skeleton"; // Import ShadCN Skeleton component

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
      setProblems(response.data);
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

  // Render the list of problems
  return (
    <div className="h-screen w-screen flex flex-col bg-[#1e1e1e] text-white p-4">
      <h2 className="text-xl font-semibold mb-4">Select a Problem</h2>
      <ul>
        {problems.map((problem: Problem) => (
          <li key={problem.id} className="mb-2">
            <button
              onClick={() => handleProblemSelect(problem)}
              className="bg-[#007acc] text-white px-4 py-2 rounded-md"
            >
              {problem.title}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default ProblemSelection;
