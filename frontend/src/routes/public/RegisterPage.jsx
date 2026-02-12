// Register Page Component
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../../store/useAuthStore";
import { authService } from "../../services/authService";
import { SignupForm } from "../../components/forms";

export default function RegisterPage() {
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  const { actions } = useAuthStore();

  const handleSubmit = async (formData) => {
    setError("");
    setIsLoading(true);

    try {
      const response = await authService.register({
        email: formData.email,
        password: formData.password,
        full_name: formData.name,
        target_exam: formData.targetExam,
      });

      // Auto-login after successful registration
      actions.setUser(response.user, response.access_token);

      navigate("/dashboard", { replace: true });
    } catch (err) {
      const message =
        err.response?.data?.detail || "Registration failed. Please try again.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleLogin = async (credential) => {
    setError("");
    setIsLoading(true);

    try {
      const response = await authService.googleLogin(credential);

      // Store user and token
      actions.setUser(response.user, response.access_token);

      navigate("/dashboard", { replace: true });
    } catch (err) {
      const message =
        err.response?.data?.detail ||
        "Google sign-up failed. Please try again.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <SignupForm
      onSubmit={handleSubmit}
      onGoogleLogin={handleGoogleLogin}
      isLoading={isLoading}
      error={error}
    />
  );
}
