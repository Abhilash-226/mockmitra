// Exams List Page Component
import { useNavigate } from "react-router-dom";
import { ExamSelectionForm } from "../../components/forms";
import { generateRoute } from "../../config/routes";

export default function ExamsListPage() {
  const navigate = useNavigate();

  const handleSelectExam = (exam) => {
    if (!exam?.id) return;
    navigate(generateRoute.examCustomize(exam.id), {
      state: { exam },
    });
  };

  return (
    <div className="max-w-6xl mx-auto">
      <ExamSelectionForm onSelect={handleSelectExam} />
    </div>
  );
}
