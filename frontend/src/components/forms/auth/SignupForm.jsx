// Signup Form Component
import { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import FormInput from "../common/FormInput";
import FormSelect from "../common/FormSelect";
import FormCheckbox from "../common/FormCheckbox";
import FormError from "../common/FormError";
import Button from "../../ui/Button";
import { GOOGLE_CLIENT_ID } from "../../../services/authService";

const EXAM_OPTIONS = [
  { value: "", label: "Select your target exam", disabled: true },
  { value: "ssc_cgl", label: "SSC CGL" },
  { value: "ssc_chsl", label: "SSC CHSL" },
  { value: "ibps_po", label: "IBPS PO" },
  { value: "ibps_clerk", label: "IBPS Clerk" },
  { value: "sbi_po", label: "SBI PO" },
  { value: "rrb_ntpc", label: "RRB NTPC" },
  { value: "upsc_cse", label: "UPSC CSE" },
  { value: "other", label: "Other" },
];

export default function SignupForm({
  onSubmit,
  onGoogleLogin,
  isLoading,
  error,
}) {
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    phone: "",
    password: "",
    confirmPassword: "",
    targetExam: "",
    acceptTerms: false,
  });
  const [errors, setErrors] = useState({});
  const [showPassword, setShowPassword] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const googleButtonRef = useRef(null);

  // Initialize Google Sign-In button
  useEffect(() => {
    if (!window.google || !onGoogleLogin || !googleButtonRef.current) return;

    try {
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: async (response) => {
          if (response.credential) {
            setGoogleLoading(true);
            try {
              await onGoogleLogin(response.credential);
            } catch (err) {
              console.error("Google signup error:", err);
            } finally {
              setGoogleLoading(false);
            }
          }
        },
        use_fedcm_for_prompt: false, // Disable FedCM to avoid CORS issues
      });

      window.google.accounts.id.renderButton(googleButtonRef.current, {
        type: "standard",
        theme: "outline",
        size: "large",
        text: "signup_with",
        width: "100%",
      });
    } catch (err) {
      console.error("Google Sign-In initialization error:", err);
    }
  }, [onGoogleLogin]);

  const validateForm = () => {
    const newErrors = {};

    if (!formData.name.trim()) {
      newErrors.name = "Name is required";
    } else if (formData.name.trim().length < 2) {
      newErrors.name = "Name must be at least 2 characters";
    }

    if (!formData.email) {
      newErrors.email = "Email is required";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = "Enter a valid email address";
    }

    if (formData.phone && !/^[0-9]{10}$/.test(formData.phone)) {
      newErrors.phone = "Enter a valid 10-digit phone number";
    }

    if (!formData.password) {
      newErrors.password = "Password is required";
    } else if (formData.password.length < 8) {
      newErrors.password = "Password must be at least 8 characters";
    } else if (!/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/.test(formData.password)) {
      newErrors.password =
        "Password must contain uppercase, lowercase, and number";
    }

    if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = "Passwords do not match";
    }

    if (!formData.targetExam) {
      newErrors.targetExam = "Please select your target exam";
    }

    if (!formData.acceptTerms) {
      newErrors.acceptTerms = "You must accept the terms and conditions";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: "" }));
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (validateForm()) {
      onSubmit(formData);
    }
  };

  const getPasswordStrength = () => {
    const { password } = formData;
    if (!password) return null;

    let strength = 0;
    if (password.length >= 8) strength++;
    if (/[a-z]/.test(password)) strength++;
    if (/[A-Z]/.test(password)) strength++;
    if (/\d/.test(password)) strength++;
    if (/[^a-zA-Z0-9]/.test(password)) strength++;

    if (strength <= 2)
      return { label: "Weak", color: "bg-red-500", width: "33%" };
    if (strength <= 3)
      return { label: "Medium", color: "bg-yellow-500", width: "66%" };
    return { label: "Strong", color: "bg-green-500", width: "100%" };
  };

  const passwordStrength = getPasswordStrength();

  return (
    <div className="bg-white rounded-xl shadow-lg p-8 w-full max-w-md">
      {/* Header */}
      <div className="text-center mb-8">
        <div className="w-12 h-12 bg-blue-600 rounded-xl flex items-center justify-center mx-auto mb-4">
          <span className="text-white font-bold text-2xl">M</span>
        </div>
        <h1 className="text-2xl font-bold text-gray-900">
          Create your account
        </h1>
        <p className="text-gray-600 mt-2">
          Start your preparation journey today
        </p>
      </div>

      {error && <FormError message={error} className="mb-6" />}

      <form onSubmit={handleSubmit} className="space-y-4">
        <FormInput
          label="Full Name"
          type="text"
          name="name"
          value={formData.name}
          onChange={handleChange}
          error={errors.name}
          placeholder="Enter your full name"
          required
          autoComplete="name"
        />

        <FormInput
          label="Email Address"
          type="email"
          name="email"
          value={formData.email}
          onChange={handleChange}
          error={errors.email}
          placeholder="you@example.com"
          required
          autoComplete="email"
        />

        <FormInput
          label="Phone Number"
          type="tel"
          name="phone"
          value={formData.phone}
          onChange={handleChange}
          error={errors.phone}
          placeholder="9876543210"
          helperText="Optional - for OTP verification"
          autoComplete="tel"
        />

        <div className="space-y-1">
          <FormInput
            label="Password"
            type={showPassword ? "text" : "password"}
            name="password"
            value={formData.password}
            onChange={handleChange}
            error={errors.password}
            placeholder="Create a strong password"
            required
            autoComplete="new-password"
            rightIcon={
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="text-gray-400 hover:text-gray-600"
              >
                {showPassword ? (
                  <svg
                    className="w-5 h-5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"
                    />
                  </svg>
                ) : (
                  <svg
                    className="w-5 h-5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                    />
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                    />
                  </svg>
                )}
              </button>
            }
          />
          {passwordStrength && (
            <div className="flex items-center gap-2">
              <div className="flex-1 h-1 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className={`h-full ${passwordStrength.color} transition-all`}
                  style={{ width: passwordStrength.width }}
                />
              </div>
              <span
                className={`text-xs font-medium ${
                  passwordStrength.label === "Weak"
                    ? "text-red-600"
                    : passwordStrength.label === "Medium"
                      ? "text-yellow-600"
                      : "text-green-600"
                }`}
              >
                {passwordStrength.label}
              </span>
            </div>
          )}
        </div>

        <FormInput
          label="Confirm Password"
          type="password"
          name="confirmPassword"
          value={formData.confirmPassword}
          onChange={handleChange}
          error={errors.confirmPassword}
          placeholder="Confirm your password"
          required
          autoComplete="new-password"
        />

        <FormSelect
          label="Target Exam"
          name="targetExam"
          value={formData.targetExam}
          onChange={handleChange}
          options={EXAM_OPTIONS}
          error={errors.targetExam}
          required
        />

        <FormCheckbox
          label={
            <span>
              I agree to the{" "}
              <Link to="/terms" className="text-blue-600 hover:underline">
                Terms of Service
              </Link>{" "}
              and{" "}
              <Link to="/privacy" className="text-blue-600 hover:underline">
                Privacy Policy
              </Link>
            </span>
          }
          name="acceptTerms"
          checked={formData.acceptTerms}
          onChange={handleChange}
          error={errors.acceptTerms}
        />

        <Button
          type="submit"
          variant="primary"
          size="lg"
          className="w-full mt-6"
          isLoading={isLoading}
        >
          Create Account
        </Button>

        {/* Divider */}
        <div className="relative my-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-gray-200"></div>
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-2 bg-white text-gray-500">
              Or continue with
            </span>
          </div>
        </div>

        {/* Google Sign-Up */}
        <div className="flex justify-center">
          <div
            ref={googleButtonRef}
            className="w-full flex justify-center"
            style={{ minHeight: "44px" }}
          >
            {/* Google Sign-In button will be rendered here */}
            {!window.google && (
              <div className="text-sm text-gray-500">
                Loading Google Sign-In...
              </div>
            )}
          </div>
        </div>
      </form>

      <p className="text-center text-sm text-gray-600 mt-8">
        Already have an account?{" "}
        <Link
          to="/login"
          className="text-blue-600 hover:text-blue-700 font-semibold"
        >
          Sign in
        </Link>
      </p>
    </div>
  );
}
