/**
 * React Frontend - Authentication & Prompt Interface
 * Demonstrates JWT authentication and prompt refinement UI for Promptheus
 */

import React, { useState, useEffect, createContext, useContext } from 'react';
import axios, { AxiosInstance } from 'axios';

// ============================================================================
// API CLIENT SETUP
// ============================================================================

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Create axios instance with default config
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor to handle token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // If access token expired, try to refresh
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem('refresh_token');
        const response = await axios.post(`${API_BASE_URL}/api/v1/auth/refresh`, {
          refresh_token: refreshToken,
        });

        const { access_token, refresh_token: newRefreshToken } = response.data;

        localStorage.setItem('access_token', access_token);
        localStorage.setItem('refresh_token', newRefreshToken);

        originalRequest.headers.Authorization = `Bearer ${access_token}`;
        return apiClient(originalRequest);
      } catch (refreshError) {
        // Refresh failed, redirect to login
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

// ============================================================================
// TYPE DEFINITIONS
// ============================================================================

interface User {
  id: string;
  email: string;
  username: string;
  full_name?: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  team_id?: string;
  team_name?: string;
}

interface LoginCredentials {
  email: string;
  password: string;
}

interface RegisterData {
  email: string;
  username: string;
  password: string;
  full_name?: string;
}

interface Question {
  question: string;
  type: 'text' | 'radio' | 'checkbox';
  options?: string[];
  required: boolean;
  default: string;
}

interface PromptHistory {
  id: string;
  original_prompt: string;
  refined_prompt: string;
  task_type?: string;
  provider: string;
  model: string;
  created_at: string;
  is_shared: boolean;
}

// ============================================================================
// AUTH CONTEXT
// ============================================================================

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Check if user is logged in on mount
    const token = localStorage.getItem('access_token');
    if (token) {
      fetchCurrentUser();
    } else {
      setIsLoading(false);
    }
  }, []);

  const fetchCurrentUser = async () => {
    try {
      const response = await apiClient.get('/api/v1/auth/me');
      setUser(response.data);
    } catch (error) {
      console.error('Failed to fetch user:', error);
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (credentials: LoginCredentials) => {
    const response = await apiClient.post('/api/v1/auth/login', credentials);
    const { access_token, refresh_token } = response.data;

    localStorage.setItem('access_token', access_token);
    localStorage.setItem('refresh_token', refresh_token);

    await fetchCurrentUser();
  };

  const register = async (data: RegisterData) => {
    await apiClient.post('/api/v1/auth/register', data);
    // After registration, automatically log in
    await login({ email: data.email, password: data.password });
  };

  const logout = async () => {
    const refreshToken = localStorage.getItem('refresh_token');
    if (refreshToken) {
      try {
        await apiClient.post('/api/v1/auth/logout', { refresh_token: refreshToken });
      } catch (error) {
        console.error('Logout error:', error);
      }
    }

    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

// ============================================================================
// LOGIN COMPONENT
// ============================================================================

export const LoginPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await login({ email, password });
      // Navigation handled by AuthProvider
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-indigo-100 via-purple-50 to-pink-100">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-2xl p-8 space-y-6">
        {/* Logo */}
        <div className="text-center">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
            Promptheus
          </h1>
          <p className="text-gray-600 mt-2">AI-Powered Prompt Engineering</p>
        </div>

        {/* Login Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition"
              placeholder="you@example.com"
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition"
              placeholder="••••••••"
            />
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 text-white py-3 rounded-lg font-semibold hover:from-indigo-700 hover:to-purple-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        {/* Demo Credentials */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm">
          <p className="font-semibold text-blue-900 mb-1">Demo Credentials:</p>
          <p className="text-blue-700">Email: demo@promptheus.dev</p>
          <p className="text-blue-700">Password: DemoPassword123!</p>
        </div>

        {/* Footer */}
        <div className="text-center text-sm text-gray-600">
          Don't have an account?{' '}
          <a href="/register" className="text-indigo-600 hover:text-indigo-800 font-semibold">
            Sign up
          </a>
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// REGISTER COMPONENT
// ============================================================================

export const RegisterPage: React.FC = () => {
  const [formData, setFormData] = useState({
    email: '',
    username: '',
    password: '',
    confirmPassword: '',
    full_name: '',
  });
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { register } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (formData.password.length < 12) {
      setError('Password must be at least 12 characters long');
      return;
    }

    setIsLoading(true);

    try {
      await register({
        email: formData.email,
        username: formData.username,
        password: formData.password,
        full_name: formData.full_name || undefined,
      });
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Registration failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-indigo-100 via-purple-50 to-pink-100 py-12">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-2xl p-8 space-y-6">
        <div className="text-center">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
            Create Account
          </h1>
          <p className="text-gray-600 mt-2">Join Promptheus today</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
              Email *
            </label>
            <input
              id="email"
              name="email"
              type="email"
              value={formData.email}
              onChange={handleChange}
              required
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
          </div>

          <div>
            <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-1">
              Username *
            </label>
            <input
              id="username"
              name="username"
              type="text"
              value={formData.username}
              onChange={handleChange}
              required
              minLength={3}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
          </div>

          <div>
            <label htmlFor="full_name" className="block text-sm font-medium text-gray-700 mb-1">
              Full Name (optional)
            </label>
            <input
              id="full_name"
              name="full_name"
              type="text"
              value={formData.full_name}
              onChange={handleChange}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
              Password * (min 12 characters)
            </label>
            <input
              id="password"
              name="password"
              type="password"
              value={formData.password}
              onChange={handleChange}
              required
              minLength={12}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
          </div>

          <div>
            <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700 mb-1">
              Confirm Password *
            </label>
            <input
              id="confirmPassword"
              name="confirmPassword"
              type="password"
              value={formData.confirmPassword}
              onChange={handleChange}
              required
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 text-white py-3 rounded-lg font-semibold hover:from-indigo-700 hover:to-purple-700 transition disabled:opacity-50"
          >
            {isLoading ? 'Creating account...' : 'Create Account'}
          </button>
        </form>

        <div className="text-center text-sm text-gray-600">
          Already have an account?{' '}
          <a href="/login" className="text-indigo-600 hover:text-indigo-800 font-semibold">
            Sign in
          </a>
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// PROMPT REFINEMENT COMPONENT
// ============================================================================

export const PromptRefinementPage: React.FC = () => {
  const [prompt, setPrompt] = useState('');
  const [questions, setQuestions] = useState<Question[]>([]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [refinedPrompt, setRefinedPrompt] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isRefining, setIsRefining] = useState(false);
  const [step, setStep] = useState<'input' | 'questions' | 'result'>('input');
  const { user } = useAuth();

  const analyzePrompt = async () => {
    setIsAnalyzing(true);
    try {
      const response = await apiClient.post('/api/v1/prompts/analyze', {
        prompt,
        provider: 'gemini',
      });

      setQuestions(response.data.questions);
      setStep('questions');
    } catch (error) {
      console.error('Analysis error:', error);
      alert('Failed to analyze prompt. Please try again.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const refinePrompt = async () => {
    setIsRefining(true);
    try {
      const response = await apiClient.post('/api/v1/prompts/refine', {
        prompt,
        answers,
        task_type: 'generation',
      });

      setRefinedPrompt(response.data.refined_prompt);
      setStep('result');
    } catch (error) {
      console.error('Refinement error:', error);
      alert('Failed to refine prompt. Please try again.');
    } finally {
      setIsRefining(false);
    }
  };

  const copyToClipboard = () => {
    navigator.clipboard.writeText(refinedPrompt);
    alert('Copied to clipboard!');
  };

  const reset = () => {
    setPrompt('');
    setQuestions([]);
    setAnswers({});
    setRefinedPrompt('');
    setStep('input');
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <h1 className="text-2xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
            Promptheus
          </h1>
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-600">Welcome, {user?.username}!</span>
            <a
              href="/history"
              className="text-sm text-indigo-600 hover:text-indigo-800 font-medium"
            >
              History
            </a>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {step === 'input' && (
          <div className="bg-white rounded-xl shadow-lg p-8 space-y-6">
            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">
                What would you like to create?
              </h2>
              <p className="text-gray-600">
                Enter your initial prompt and we'll help refine it into something amazing.
              </p>
            </div>

            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="E.g., Write a blog post about AI in healthcare..."
              rows={6}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
            />

            <button
              onClick={analyzePrompt}
              disabled={!prompt.trim() || isAnalyzing}
              className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 text-white py-3 rounded-lg font-semibold hover:from-indigo-700 hover:to-purple-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isAnalyzing ? 'Analyzing...' : 'Refine My Prompt →'}
            </button>
          </div>
        )}

        {step === 'questions' && (
          <div className="bg-white rounded-xl shadow-lg p-8 space-y-6">
            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">
                Help us understand your needs
              </h2>
              <p className="text-gray-600">
                Answer a few questions to get the best refined prompt.
              </p>
            </div>

            {questions.map((q, idx) => (
              <div key={idx} className="space-y-2">
                <label className="block text-sm font-medium text-gray-900">
                  {q.question}
                  {!q.required && <span className="text-gray-500 ml-1">(optional)</span>}
                </label>

                {q.type === 'text' && (
                  <input
                    type="text"
                    value={answers[`q${idx}`] || ''}
                    onChange={(e) => setAnswers({ ...answers, [`q${idx}`]: e.target.value })}
                    required={q.required}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  />
                )}

                {q.type === 'radio' && (
                  <div className="space-y-2">
                    {q.options?.map((option) => (
                      <label key={option} className="flex items-center space-x-2">
                        <input
                          type="radio"
                          name={`q${idx}`}
                          value={option}
                          checked={answers[`q${idx}`] === option}
                          onChange={(e) => setAnswers({ ...answers, [`q${idx}`]: e.target.value })}
                          className="text-indigo-600 focus:ring-indigo-500"
                        />
                        <span className="text-gray-700">{option}</span>
                      </label>
                    ))}
                  </div>
                )}
              </div>
            ))}

            <div className="flex gap-4">
              <button
                onClick={() => setStep('input')}
                className="flex-1 bg-gray-100 text-gray-700 py-3 rounded-lg font-semibold hover:bg-gray-200 transition"
              >
                ← Back
              </button>
              <button
                onClick={refinePrompt}
                disabled={isRefining}
                className="flex-1 bg-gradient-to-r from-indigo-600 to-purple-600 text-white py-3 rounded-lg font-semibold hover:from-indigo-700 hover:to-purple-700 transition disabled:opacity-50"
              >
                {isRefining ? 'Refining...' : 'Generate Refined Prompt →'}
              </button>
            </div>
          </div>
        )}

        {step === 'result' && (
          <div className="space-y-6">
            {/* Original Prompt */}
            <div className="bg-white rounded-xl shadow-lg p-8">
              <h3 className="text-lg font-semibold text-gray-700 mb-3">Your Original Prompt</h3>
              <p className="text-gray-600 bg-gray-50 p-4 rounded-lg">{prompt}</p>
            </div>

            {/* Refined Prompt */}
            <div className="bg-gradient-to-br from-indigo-50 to-purple-50 rounded-xl shadow-lg p-8 border-2 border-indigo-200">
              <div className="flex justify-between items-center mb-3">
                <h3 className="text-lg font-semibold text-gray-900">Refined Prompt</h3>
                <button
                  onClick={copyToClipboard}
                  className="px-4 py-2 bg-white text-indigo-600 rounded-lg font-medium hover:bg-indigo-50 transition border border-indigo-200"
                >
                  📋 Copy
                </button>
              </div>
              <pre className="text-gray-800 bg-white p-6 rounded-lg overflow-auto whitespace-pre-wrap">
                {refinedPrompt}
              </pre>
            </div>

            {/* Actions */}
            <div className="flex gap-4">
              <button
                onClick={reset}
                className="flex-1 bg-gray-100 text-gray-700 py-3 rounded-lg font-semibold hover:bg-gray-200 transition"
              >
                ← Create New Prompt
              </button>
              <a
                href="/history"
                className="flex-1 bg-indigo-600 text-white py-3 rounded-lg font-semibold hover:bg-indigo-700 transition text-center"
              >
                View History →
              </a>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

// ============================================================================
// HISTORY COMPONENT
// ============================================================================

export const HistoryPage: React.FC = () => {
  const [history, setHistory] = useState<PromptHistory[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedPrompt, setSelectedPrompt] = useState<PromptHistory | null>(null);

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    try {
      const response = await apiClient.get('/api/v1/prompts/history', {
        params: { limit: 50 },
      });
      setHistory(response.data);
    } catch (error) {
      console.error('Failed to fetch history:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const deletePrompt = async (id: string) => {
    if (!confirm('Are you sure you want to delete this prompt?')) return;

    try {
      await apiClient.delete(`/api/v1/prompts/${id}`);
      setHistory(history.filter((p) => p.id !== id));
      if (selectedPrompt?.id === id) setSelectedPrompt(null);
    } catch (error) {
      console.error('Failed to delete prompt:', error);
      alert('Failed to delete prompt. Please try again.');
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-gray-600">Loading history...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b mb-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center gap-4">
            <a href="/" className="text-indigo-600 hover:text-indigo-800">
              ← Back
            </a>
            <h1 className="text-2xl font-bold text-gray-900">Prompt History</h1>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* History List */}
          <div className="lg:col-span-1 space-y-4">
            {history.length === 0 ? (
              <div className="bg-white rounded-xl shadow p-8 text-center text-gray-500">
                No prompts yet. Create your first one!
              </div>
            ) : (
              history.map((item) => (
                <div
                  key={item.id}
                  onClick={() => setSelectedPrompt(item)}
                  className={`bg-white rounded-lg shadow p-4 cursor-pointer transition hover:shadow-md ${
                    selectedPrompt?.id === item.id ? 'ring-2 ring-indigo-500' : ''
                  }`}
                >
                  <div className="text-sm text-gray-500 mb-2">
                    {new Date(item.created_at).toLocaleDateString()}
                  </div>
                  <div className="text-gray-900 font-medium line-clamp-2">
                    {item.original_prompt}
                  </div>
                  <div className="flex items-center gap-2 mt-2">
                    <span className="text-xs bg-indigo-100 text-indigo-700 px-2 py-1 rounded">
                      {item.provider}
                    </span>
                    {item.task_type && (
                      <span className="text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded">
                        {item.task_type}
                      </span>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Prompt Detail */}
          <div className="lg:col-span-2">
            {selectedPrompt ? (
              <div className="bg-white rounded-xl shadow-lg p-8 space-y-6">
                <div className="flex justify-between items-start">
                  <div>
                    <h2 className="text-xl font-bold text-gray-900">Prompt Details</h2>
                    <p className="text-sm text-gray-500 mt-1">
                      Created {new Date(selectedPrompt.created_at).toLocaleString()}
                    </p>
                  </div>
                  <button
                    onClick={() => deletePrompt(selectedPrompt.id)}
                    className="text-red-600 hover:text-red-800 text-sm font-medium"
                  >
                    🗑️ Delete
                  </button>
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-2">Original Prompt</h3>
                  <p className="text-gray-600 bg-gray-50 p-4 rounded-lg">
                    {selectedPrompt.original_prompt}
                  </p>
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-2">Refined Prompt</h3>
                  <pre className="text-gray-800 bg-gradient-to-br from-indigo-50 to-purple-50 p-6 rounded-lg overflow-auto whitespace-pre-wrap border-2 border-indigo-100">
                    {selectedPrompt.refined_prompt}
                  </pre>
                </div>

                <button
                  onClick={() => navigator.clipboard.writeText(selectedPrompt.refined_prompt)}
                  className="w-full bg-indigo-600 text-white py-3 rounded-lg font-semibold hover:bg-indigo-700 transition"
                >
                  📋 Copy Refined Prompt
                </button>
              </div>
            ) : (
              <div className="bg-white rounded-xl shadow-lg p-12 text-center text-gray-500">
                Select a prompt from the list to view details
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// MAIN APP COMPONENT
// ============================================================================

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  );
};

const AppRoutes: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-gray-600">Loading...</div>
      </div>
    );
  }

  // Simple client-side routing (use React Router in production)
  const path = window.location.pathname;

  if (!isAuthenticated) {
    if (path === '/register') return <RegisterPage />;
    return <LoginPage />;
  }

  if (path === '/history') return <HistoryPage />;
  return <PromptRefinementPage />;
};

export default App;
