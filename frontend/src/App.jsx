import { createBrowserRouter, RouterProvider, createRoutesFromElements, Routes, Route, Navigate, Outlet } from "react-router-dom";
import { useAuthStore } from "./store/useAuthStore";

// Layout Components
import {
  Navbar,
  Footer,
  PageContainer,
  AuthContainer,
} from "./components/layout";

// Auth Pages
import LoginPage from "./routes/public/LoginPage";
import RegisterPage from "./routes/public/RegisterPage";
import LandingPage from "./routes/public/LandingPage";
import ForgotPasswordPage from "./routes/public/ForgotPasswordPage";

// Dashboard Pages
import DashboardPage from "./routes/dashboard/DashboardPage";
import ExamsListPage from "./routes/dashboard/ExamsListPage";
import ProfilePage from "./routes/dashboard/ProfilePage";
import HistoryPage from "./routes/dashboard/HistoryPage";
import SettingsPage from "./routes/dashboard/SettingsPage";
import PYQPapersPage from "./routes/dashboard/PYQPapersPage";

// Exam Pages
import ExamCustomizationPage from "./routes/exam/ExamCustomizationPage";
import ExamInterfacePage from "./routes/exam/ExamInterfacePage";
import ExamInstructionsPage from "./routes/exam/ExamInstructionsPage";
import PYQInstructionsPage from "./routes/exam/PYQInstructionsPage";
import PYQExamInterfacePage from "./routes/exam/PYQExamInterfacePage";

// Results Pages
import ResultsSummaryPage from "./routes/results/ResultsSummaryPage";
import DetailedAnalysisPage from "./routes/results/DetailedAnalysisPage";
import AnalyticsPage from "./routes/results/AnalyticsPage";
import ResultsPage from "./routes/results/ResultsPage";

// Common Components
import ProtectedRoute from "./components/common/ProtectedRoute";
import ExamGuard from "./components/common/ExamGuard";

import "./App.css";

// Separate Layout Helper for better organization with createBrowserRouter
const AppLayout = () => {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Outlet />
    </div>
  );
};

// Define routes using createBrowserRouter for v6.4+ Data API support
const getRouter = (isAuthenticated) => createBrowserRouter(
  createRoutesFromElements(
    <Route path="/" element={<AppLayout />}>
      {/* Public Routes */}
      <Route
        index
        element={
          <>
            <Navbar user={isAuthenticated ? { name: "User" } : null} />
            <LandingPage />
            <Footer />
          </>
        }
      />

      <Route
        path="login"
        element={
          isAuthenticated ? (
            <Navigate to="/dashboard" replace />
          ) : (
            <AuthContainer>
              <LoginPage />
            </AuthContainer>
          )
        }
      />

      <Route
        path="signup"
        element={
          isAuthenticated ? (
            <Navigate to="/dashboard" replace />
          ) : (
            <AuthContainer>
              <RegisterPage />
            </AuthContainer>
          )
        }
      />

      <Route
        path="forgot-password"
        element={
          isAuthenticated ? (
            <Navigate to="/dashboard" replace />
          ) : (
            <ForgotPasswordPage />
          )
        }
      />

      {/* Protected Dashboard Routes */}
      <Route
        path="dashboard"
        element={
          <ProtectedRoute>
            <Navbar user={{ name: "User" }} />
            <PageContainer title="Dashboard">
              <DashboardPage />
            </PageContainer>
          </ProtectedRoute>
        }
      />

      <Route
        path="dashboard/exams"
        element={
          <ProtectedRoute>
            <Navbar user={{ name: "User" }} />
            <PageContainer title="Available Exams">
              <ExamsListPage />
            </PageContainer>
          </ProtectedRoute>
        }
      />

      <Route
        path="profile"
        element={
          <ProtectedRoute>
            <Navbar user={{ name: "User" }} />
            <PageContainer title="Profile Settings">
              <ProfilePage />
            </PageContainer>
          </ProtectedRoute>
        }
      />

      <Route
        path="history"
        element={
          <ProtectedRoute>
            <Navbar user={{ name: "User" }} />
            <PageContainer title="Test History">
              <HistoryPage />
            </PageContainer>
          </ProtectedRoute>
        }
      />

      <Route
        path="pyq-papers"
        element={
          <ProtectedRoute>
            <Navbar user={{ name: "User" }} />
            <PageContainer title="PYQ Papers">
              <PYQPapersPage />
            </PageContainer>
          </ProtectedRoute>
        }
      />

      <Route
        path="exams"
        element={
          <ProtectedRoute>
            <Navbar user={{ name: "User" }} />
            <PageContainer title="Available Exams">
              <ExamsListPage />
            </PageContainer>
          </ProtectedRoute>
        }
      />

      <Route
        path="settings"
        element={
          <ProtectedRoute>
            <Navbar user={{ name: "User" }} />
            <PageContainer title="Settings">
              <SettingsPage />
            </PageContainer>
          </ProtectedRoute>
        }
      />

      <Route
        path="analytics"
        element={
          <ProtectedRoute>
            <Navbar user={{ name: "User" }} />
            <PageContainer title="Analytics">
              <AnalyticsPage />
            </PageContainer>
          </ProtectedRoute>
        }
      />

      <Route
        path="results"
        element={
          <ProtectedRoute>
            <Navbar user={{ name: "User" }} />
            <PageContainer title="Test Results">
              <ResultsPage />
            </PageContainer>
          </ProtectedRoute>
        }
      />

      {/* Exam Routes */}
      <Route
        path="exam/customize"
        element={
          <ProtectedRoute>
            <Navbar user={{ name: "User" }} />
            <PageContainer title="Create Custom Test">
              <ExamCustomizationPage />
            </PageContainer>
          </ProtectedRoute>
        }
      />

      <Route
        path="exam/:examId/customize"
        element={
          <ProtectedRoute>
            <Navbar user={{ name: "User" }} />
            <PageContainer title="Customize Test">
              <ExamCustomizationPage />
            </PageContainer>
          </ProtectedRoute>
        }
      />

      <Route
        path="exam/:examId/instructions"
        element={
          <ExamGuard>
            <ExamInstructionsPage />
          </ExamGuard>
        }
      />

      <Route
        path="exam/:examId/test"
        element={
          <ExamGuard>
            <ExamInterfacePage />
          </ExamGuard>
        }
      />

      {/* PYQ Routes */}
      <Route
        path="pyq/:paperId/instructions"
        element={
          <ProtectedRoute>
            <PYQInstructionsPage />
          </ProtectedRoute>
        }
      />

      <Route
        path="pyq/:paperId/test"
        element={
          <ProtectedRoute>
            <PYQExamInterfacePage />
          </ProtectedRoute>
        }
      />

      {/* Results Routes */}
      <Route
        path="results/:attemptId"
        element={
          <ProtectedRoute>
            <Navbar user={{ name: "User" }} />
            <PageContainer title="Results">
              <DetailedAnalysisPage />
            </PageContainer>
          </ProtectedRoute>
        }
      />

      {/* Backward-compat: /analysis redirects to parent */}
      <Route
        path="results/:attemptId/analysis"
        element={<Navigate to=".." relative="path" replace />}
      />

      {/* Catch-all redirect */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Route>
  )
);

function App() {
  const { isAuthenticated } = useAuthStore();
  
  // Note: For complex state changes that affect routing (like Auth), 
  // we might want useMemo here, but simple isAuthenticated is usually fine.
  const router = getRouter(isAuthenticated);

  return <RouterProvider router={router} />;
}

export default App;
