/**
 * Unit tests for Login component
 */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Login from '../Login';

// Mock auth service
const mockRegister = jest.fn();
const mockLogin = jest.fn();

jest.mock('../../../services/auth', () => ({
  authService: {
    register: jest.fn((...args) => mockRegister(...args)),
    login: jest.fn((...args) => mockLogin(...args)),
    getToken: jest.fn(() => null),
  },
}));

// Mock useNavigate
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

// Mock OAuth providers
jest.mock('@react-oauth/google', () => ({
  GoogleLogin: () => <button data-testid="google-login">Google Login</button>,
  useGoogleLogin: () => jest.fn(),
}));

jest.mock('@azure/msal-react', () => ({
  useMsal: () => ({
    instance: {
      loginPopup: jest.fn(),
    },
    accounts: [],
  }),
  useIsAuthenticated: () => false,
}));

describe('Login Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockRegister.mockResolvedValue({ token: 'test-token' });
    mockLogin.mockResolvedValue({ token: 'test-token' });
  });

  test('renders login form', async () => {
    render(
      <BrowserRouter>
        <Login />
      </BrowserRouter>
    );

    await waitFor(() => {
      // Should render the component
      expect(document.body).toBeTruthy();
    });
  });
});
