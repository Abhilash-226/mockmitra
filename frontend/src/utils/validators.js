/**
 * Validation Functions
 */

export const validators = {
  required: (value) => {
    if (value === null || value === undefined || value === "") {
      return "This field is required";
    }
    return null;
  },

  email: (value) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(value)) {
      return "Please enter a valid email address";
    }
    return null;
  },

  phone: (value) => {
    const phoneRegex = /^[6-9]\d{9}$/;
    if (!phoneRegex.test(value)) {
      return "Please enter a valid 10-digit phone number";
    }
    return null;
  },

  minLength: (min) => (value) => {
    if (value.length < min) {
      return `Minimum ${min} characters required`;
    }
    return null;
  },

  maxLength: (max) => (value) => {
    if (value.length > max) {
      return `Maximum ${max} characters allowed`;
    }
    return null;
  },

  password: (value) => {
    if (value.length < 8) {
      return "Password must be at least 8 characters";
    }
    if (!/[A-Z]/.test(value)) {
      return "Password must contain at least one uppercase letter";
    }
    if (!/[0-9]/.test(value)) {
      return "Password must contain at least one number";
    }
    return null;
  },

  confirmPassword: (password) => (value) => {
    if (value !== password) {
      return "Passwords do not match";
    }
    return null;
  },
};

// Validate form data against schema
export function validateForm(data, schema) {
  const errors = {};

  Object.keys(schema).forEach((field) => {
    const rules = schema[field];
    const value = data[field];

    for (const rule of rules) {
      const error = rule(value);
      if (error) {
        errors[field] = error;
        break;
      }
    }
  });

  return {
    isValid: Object.keys(errors).length === 0,
    errors,
  };
}
