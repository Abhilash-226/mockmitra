/**
 * useForm Hook - Generic form state management
 */

import { useState, useCallback } from "react";

export default function useForm(initialValues = {}, validationSchema = {}) {
  const [values, setValues] = useState(initialValues);
  const [errors, setErrors] = useState({});
  const [touched, setTouched] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleChange = useCallback((e) => {
    const { name, value, type, checked } = e.target;
    setValues((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
  }, []);

  const handleBlur = useCallback((e) => {
    const { name } = e.target;
    setTouched((prev) => ({ ...prev, [name]: true }));
  }, []);

  const validate = useCallback(() => {
    const newErrors = {};

    Object.keys(validationSchema).forEach((field) => {
      const rules = validationSchema[field];
      const value = values[field];

      if (rules.required && !value) {
        newErrors[field] = rules.message || "This field is required";
      } else if (rules.minLength && value.length < rules.minLength) {
        newErrors[field] = `Minimum ${rules.minLength} characters required`;
      } else if (rules.pattern && !rules.pattern.test(value)) {
        newErrors[field] = rules.message || "Invalid format";
      } else if (rules.match && value !== values[rules.match]) {
        newErrors[field] = rules.message || "Fields do not match";
      }
    });

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [values, validationSchema]);

  const handleSubmit = useCallback(
    (onSubmit) => async (e) => {
      e.preventDefault();

      if (!validate()) return;

      setIsSubmitting(true);
      try {
        await onSubmit(values);
      } finally {
        setIsSubmitting(false);
      }
    },
    [values, validate],
  );

  const reset = useCallback(() => {
    setValues(initialValues);
    setErrors({});
    setTouched({});
  }, [initialValues]);

  return {
    values,
    errors,
    touched,
    isSubmitting,
    handleChange,
    handleBlur,
    handleSubmit,
    validate,
    reset,
    setValues,
    setErrors,
  };
}
