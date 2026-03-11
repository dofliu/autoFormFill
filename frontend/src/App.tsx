import { BrowserRouter, Routes, Route } from "react-router-dom";
import AppShell from "./components/layout/AppShell";
import ErrorBoundary from "./components/ErrorBoundary";
import ProtectedRoute from "./components/ProtectedRoute";
import { AuthProvider } from "./contexts/AuthContext";
import ChatPage from "./pages/ChatPage";
import EmailDraftPage from "./pages/EmailDraftPage";
import FormFillPage from "./pages/FormFillPage";
import UserProfilePage from "./pages/UserProfilePage";
import KnowledgeBasePage from "./pages/KnowledgeBasePage";
import FormPreviewPage from "./pages/FormPreviewPage";
import FormHistoryPage from "./pages/FormHistoryPage";
import IndexingStatusPage from "./pages/IndexingStatusPage";
import ReportPage from "./pages/ReportPage";
import EntityPage from "./pages/EntityPage";
import KnowledgeGraphPage from "./pages/KnowledgeGraphPage";
import CompliancePage from "./pages/CompliancePage";
import VersionPage from "./pages/VersionPage";
import ReminderPage from "./pages/ReminderPage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";

export default function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            {/* Public routes */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />

            {/* Protected routes */}
            <Route
              element={
                <ProtectedRoute>
                  <AppShell />
                </ProtectedRoute>
              }
            >
              <Route path="/" element={<FormFillPage />} />
              <Route path="/chat" element={<ChatPage />} />
              <Route path="/email" element={<EmailDraftPage />} />
              <Route path="/report" element={<ReportPage />} />
              <Route path="/profile" element={<UserProfilePage />} />
              <Route path="/entities" element={<EntityPage />} />
              <Route path="/graph" element={<KnowledgeGraphPage />} />
              <Route path="/knowledge" element={<KnowledgeBasePage />} />
              <Route path="/indexing" element={<IndexingStatusPage />} />
              <Route path="/preview/:jobId" element={<FormPreviewPage />} />
              <Route path="/compliance" element={<CompliancePage />} />
              <Route path="/versions" element={<VersionPage />} />
              <Route path="/reminders" element={<ReminderPage />} />
              <Route path="/history" element={<FormHistoryPage />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ErrorBoundary>
  );
}
