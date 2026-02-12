/**
 * Register Page Component.
 *
 * Ref: .blueprint/auth.md §5, §7
 *
 * Features:
 * - Full registration form (username, email, password, phone)
 * - Form validation
 * - Password strength indicator
 * - Error display
 * - Link to login page
 */

import { memo, useCallback, useState } from 'react';
import {
  User,
  Mail,
  Lock,
  Phone,
  UserPlus,
  Eye,
  EyeOff,
  AlertCircle,
  Check,
} from 'lucide-react';
import { useAuthStore } from '@/store';

interface RegisterPageProps {
  onSuccess?: () => void;
  onLoginClick: () => void;
}

interface FormData {
  username: string;
  email: string;
  password: string;
  password_confirm: string;
  phone: string;
}

interface FormErrors {
  username?: string;
  email?: string;
  password?: string;
  password_confirm?: string;
  phone?: string;
}

function RegisterPageComponent({ onSuccess, onLoginClick }: RegisterPageProps) {
  const { register, isLoading, error, clearError } = useAuthStore();

  const [formData, setFormData] = useState<FormData>({
    username: '',
    email: '',
    password: '',
    password_confirm: '',
    phone: '',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [formErrors, setFormErrors] = useState<FormErrors>({});

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const { name, value } = e.target;
      setFormData((prev) => ({ ...prev, [name]: value }));
      setFormErrors((prev) => ({ ...prev, [name]: undefined }));
      clearError();
    },
    [clearError]
  );

  const validateForm = useCallback((): boolean => {
    const errors: FormErrors = {};

    // Username validation
    if (!formData.username.trim()) {
      errors.username = 'Username is required';
    } else if (formData.username.length < 3) {
      errors.username = 'Username must be at least 3 characters';
    } else if (!/^[a-zA-Z0-9_]+$/.test(formData.username)) {
      errors.username = 'Username can only contain letters, numbers, and underscores';
    }

    // Email validation
    if (!formData.email.trim()) {
      errors.email = 'Email is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      errors.email = 'Please enter a valid email address';
    }

    // Password validation
    if (!formData.password) {
      errors.password = 'Password is required';
    } else if (formData.password.length < 8) {
      errors.password = 'Password must be at least 8 characters';
    }

    // Password confirm validation
    if (!formData.password_confirm) {
      errors.password_confirm = 'Please confirm your password';
    } else if (formData.password !== formData.password_confirm) {
      errors.password_confirm = 'Passwords do not match';
    }

    // Phone validation (optional but must be valid if provided)
    if (formData.phone && !/^[+]?[0-9]{8,15}$/.test(formData.phone.replace(/\s/g, ''))) {
      errors.phone = 'Please enter a valid phone number';
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  }, [formData]);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();

      if (!validateForm()) return;

      try {
        await register({
          username: formData.username.trim(),
          email: formData.email.trim(),
          password: formData.password,
          password_confirm: formData.password_confirm,
          phone: formData.phone.trim() || undefined,
        });
        onSuccess?.();
      } catch {
        // Error is handled by the store
      }
    },
    [formData, register, onSuccess, validateForm]
  );

  // Password strength indicator
  const getPasswordStrength = useCallback((password: string) => {
    let strength = 0;
    if (password.length >= 8) strength++;
    if (/[a-z]/.test(password) && /[A-Z]/.test(password)) strength++;
    if (/[0-9]/.test(password)) strength++;
    if (/[^a-zA-Z0-9]/.test(password)) strength++;
    return strength;
  }, []);

  const passwordStrength = getPasswordStrength(formData.password);
  const strengthLabels = ['Weak', 'Fair', 'Good', 'Strong'];
  const strengthColors = ['bg-red-500', 'bg-yellow-500', 'bg-blue-500', 'bg-green-500'];

  return (
    <div className="mx-auto max-w-md">
      <div className="rounded-lg border border-border bg-card p-8 shadow-lg">
        {/* Header */}
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
            <UserPlus className="h-8 w-8 text-primary" />
          </div>
          <h1 className="text-2xl font-bold text-card-foreground">Create Account</h1>
          <p className="mt-2 text-muted-foreground">
            Join us to start shopping
          </p>
        </div>

        {/* API Error Alert */}
        {error && (
          <div className="mb-6 flex items-center gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
            <AlertCircle className="h-5 w-5 flex-shrink-0" />
            <span className="text-sm">{error}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Username Field */}
          <div>
            <label
              htmlFor="username"
              className="mb-2 block text-sm font-medium text-card-foreground"
            >
              Username <span className="text-red-500">*</span>
            </label>
            <div className="relative">
              <User className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
              <input
                id="username"
                name="username"
                type="text"
                autoComplete="username"
                value={formData.username}
                onChange={handleChange}
                placeholder="Choose a username"
                className={`w-full rounded-lg border bg-background py-3 pl-10 pr-4 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 ${
                  formErrors.username
                    ? 'border-red-500 focus:border-red-500 focus:ring-red-500/20'
                    : 'border-input focus:border-primary focus:ring-primary/20'
                }`}
                disabled={isLoading}
              />
            </div>
            {formErrors.username && (
              <p className="mt-1 text-sm text-red-500">{formErrors.username}</p>
            )}
          </div>

          {/* Email Field */}
          <div>
            <label
              htmlFor="email"
              className="mb-2 block text-sm font-medium text-card-foreground"
            >
              Email <span className="text-red-500">*</span>
            </label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                value={formData.email}
                onChange={handleChange}
                placeholder="Enter your email"
                className={`w-full rounded-lg border bg-background py-3 pl-10 pr-4 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 ${
                  formErrors.email
                    ? 'border-red-500 focus:border-red-500 focus:ring-red-500/20'
                    : 'border-input focus:border-primary focus:ring-primary/20'
                }`}
                disabled={isLoading}
              />
            </div>
            {formErrors.email && (
              <p className="mt-1 text-sm text-red-500">{formErrors.email}</p>
            )}
          </div>

          {/* Phone Field (Optional) */}
          <div>
            <label
              htmlFor="phone"
              className="mb-2 block text-sm font-medium text-card-foreground"
            >
              Phone Number{' '}
              <span className="text-muted-foreground">(optional)</span>
            </label>
            <div className="relative">
              <Phone className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
              <input
                id="phone"
                name="phone"
                type="tel"
                autoComplete="tel"
                value={formData.phone}
                onChange={handleChange}
                placeholder="+852 1234 5678"
                className={`w-full rounded-lg border bg-background py-3 pl-10 pr-4 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 ${
                  formErrors.phone
                    ? 'border-red-500 focus:border-red-500 focus:ring-red-500/20'
                    : 'border-input focus:border-primary focus:ring-primary/20'
                }`}
                disabled={isLoading}
              />
            </div>
            {formErrors.phone && (
              <p className="mt-1 text-sm text-red-500">{formErrors.phone}</p>
            )}
          </div>

          {/* Password Field */}
          <div>
            <label
              htmlFor="password"
              className="mb-2 block text-sm font-medium text-card-foreground"
            >
              Password <span className="text-red-500">*</span>
            </label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
              <input
                id="password"
                name="password"
                type={showPassword ? 'text' : 'password'}
                autoComplete="new-password"
                value={formData.password}
                onChange={handleChange}
                placeholder="Create a password"
                className={`w-full rounded-lg border bg-background py-3 pl-10 pr-12 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 ${
                  formErrors.password
                    ? 'border-red-500 focus:border-red-500 focus:ring-red-500/20'
                    : 'border-input focus:border-primary focus:ring-primary/20'
                }`}
                disabled={isLoading}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                tabIndex={-1}
              >
                {showPassword ? (
                  <EyeOff className="h-5 w-5" />
                ) : (
                  <Eye className="h-5 w-5" />
                )}
              </button>
            </div>
            {formErrors.password && (
              <p className="mt-1 text-sm text-red-500">{formErrors.password}</p>
            )}
            {/* Password Strength Indicator */}
            {formData.password && (
              <div className="mt-2">
                <div className="flex gap-1">
                  {[0, 1, 2, 3].map((i) => (
                    <div
                      key={i}
                      className={`h-1 flex-1 rounded-full transition-colors ${
                        i < passwordStrength
                          ? strengthColors[passwordStrength - 1]
                          : 'bg-gray-200'
                      }`}
                    />
                  ))}
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  Password strength: {strengthLabels[passwordStrength - 1] || 'Too weak'}
                </p>
              </div>
            )}
          </div>

          {/* Confirm Password Field */}
          <div>
            <label
              htmlFor="password_confirm"
              className="mb-2 block text-sm font-medium text-card-foreground"
            >
              Confirm Password <span className="text-red-500">*</span>
            </label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
              <input
                id="password_confirm"
                name="password_confirm"
                type={showConfirmPassword ? 'text' : 'password'}
                autoComplete="new-password"
                value={formData.password_confirm}
                onChange={handleChange}
                placeholder="Confirm your password"
                className={`w-full rounded-lg border bg-background py-3 pl-10 pr-12 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 ${
                  formErrors.password_confirm
                    ? 'border-red-500 focus:border-red-500 focus:ring-red-500/20'
                    : 'border-input focus:border-primary focus:ring-primary/20'
                }`}
                disabled={isLoading}
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                tabIndex={-1}
              >
                {showConfirmPassword ? (
                  <EyeOff className="h-5 w-5" />
                ) : (
                  <Eye className="h-5 w-5" />
                )}
              </button>
              {/* Match indicator */}
              {formData.password_confirm && formData.password === formData.password_confirm && (
                <Check className="absolute right-10 top-1/2 h-5 w-5 -translate-y-1/2 text-green-500" />
              )}
            </div>
            {formErrors.password_confirm && (
              <p className="mt-1 text-sm text-red-500">{formErrors.password_confirm}</p>
            )}
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isLoading}
            className="mt-6 w-full rounded-lg bg-primary py-3 font-semibold text-primary-foreground transition-colors hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isLoading ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="h-5 w-5 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                  />
                </svg>
                Creating account...
              </span>
            ) : (
              <span className="flex items-center justify-center gap-2">
                <UserPlus className="h-5 w-5" />
                Create Account
              </span>
            )}
          </button>
        </form>

        {/* Login Link */}
        <div className="mt-6 text-center text-sm text-muted-foreground">
          Already have an account?{' '}
          <button
            onClick={onLoginClick}
            className="font-medium text-primary hover:underline"
            disabled={isLoading}
          >
            Sign In
          </button>
        </div>
      </div>
    </div>
  );
}

export const RegisterPage = memo(RegisterPageComponent);
