import { useNavigate } from "react-router-dom";
import FormUploadStep from "../components/form-fill/FormUploadStep";
import type { FormFillResponse } from "../types/form";

export default function FormFillPage() {
  const navigate = useNavigate();

  const handleFilled = (response: FormFillResponse) => {
    // Navigate to preview page with job_id
    navigate(`/preview/${response.job_id}`);
  };

  return <FormUploadStep onFilled={handleFilled} />;
}
