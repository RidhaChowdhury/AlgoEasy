import { BrowserRouter as Router, Route, Routes } from "react-router-dom";
import ProblemSelection from "@/pages/ProblemSelection";
import Problem from "@/pages/Problem";

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<ProblemSelection />} />
        <Route path="/problem/:id" element={<Problem />} />
      </Routes>
    </Router>
  );
}

export default App;
