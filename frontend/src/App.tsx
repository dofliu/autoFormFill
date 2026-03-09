import { BrowserRouter, Routes, Route } from "react-router-dom";
import AppShell from "./components/layout/AppShell";
import FormFillPage from "./pages/FormFillPage";
import UserProfilePage from "./pages/UserProfilePage";
import KnowledgeBasePage from "./pages/KnowledgeBasePage";
import FormPreviewPage from "./pages/FormPreviewPage";
import FormHistoryPage from "./pages/FormHistoryPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/" element={<FormFillPage />} />
          <Route path="/profile" element={<UserProfilePage />} />
          <Route path="/knowledge" element={<KnowledgeBasePage />} />
          <Route path="/preview/:jobId" element={<FormPreviewPage />} />
          <Route path="/history" element={<FormHistoryPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
