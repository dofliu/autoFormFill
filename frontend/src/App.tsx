import { BrowserRouter, Routes, Route } from "react-router-dom";
import AppShell from "./components/layout/AppShell";
import ChatPage from "./pages/ChatPage";
import EmailDraftPage from "./pages/EmailDraftPage";
import FormFillPage from "./pages/FormFillPage";
import UserProfilePage from "./pages/UserProfilePage";
import KnowledgeBasePage from "./pages/KnowledgeBasePage";
import FormPreviewPage from "./pages/FormPreviewPage";
import FormHistoryPage from "./pages/FormHistoryPage";
import IndexingStatusPage from "./pages/IndexingStatusPage";
import ReportPage from "./pages/ReportPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/" element={<FormFillPage />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/email" element={<EmailDraftPage />} />
          <Route path="/report" element={<ReportPage />} />
          <Route path="/profile" element={<UserProfilePage />} />
          <Route path="/knowledge" element={<KnowledgeBasePage />} />
          <Route path="/indexing" element={<IndexingStatusPage />} />
          <Route path="/preview/:jobId" element={<FormPreviewPage />} />
          <Route path="/history" element={<FormHistoryPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
