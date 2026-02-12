// Login Page Component
import { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuthStore } from "../../store/useAuthStore";
import { authService } from "../../services/authService";
import { LoginForm } from "../../components/forms";

export default function LoginPage() {
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { actions } = useAuthStore();

  const from = location.state?.from?.pathname || "/dashboard";

  const handleSubmit = async (formData) => {
    setError("");
    setIsLoading(true);

    try {
      const response = await authService.login({
        email: formData.email,
        password: formData.password,
      });

      // Store user and token
      actions.setUser(response.user, response.access_token);

      navigate(from, { replace: true });
    } catch (err) {
      const message =
        err.response?.data?.detail || "Invalid credentials. Please try again.";
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

      navigate(from, { replace: true });
    } catch (err) {
      const message =
        err.response?.data?.detail ||
        "Google sign-in failed. Please try again.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <LoginForm
      onSubmit={handleSubmit}
      onGoogleLogin={handleGoogleLogin}
      isLoading={isLoading}
      error={error}
    />
  );
}
