import { useNavigate } from "react-router-dom";

type Problem = {
  id: number;
  title: string;
  description: string;
  arguments: string;
};

const problems: Problem[] = [
  {
    id: 1,
    title: "FizzBuzz Problem",
    description:
      "Write a function `fizzbuzz(n)` that returns 'Fizz' for multiples of 3, 'Buzz' for multiples of 5, and 'FizzBuzz' for multiples of both. Otherwise, return the number itself as a string.",
    arguments: "n: int", // Arguments string with type hints
  },
  {
    id: 2,
    title: "Palindrome Problem",
    description:
      "Write a function `isPalindrome(s)` that checks if a given string is a palindrome. A palindrome is a string that reads the same backward as forward.",
    arguments: "s: str", // Arguments string with type hints
  },
];



const ProblemSelection = () => {
  const navigate = useNavigate();

  // Function to handle when a problem is selected
  const handleProblemSelect = (problem: Problem) => {
    navigate(`/problem/${problem.id}`, { state: { problem } });
  };

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
