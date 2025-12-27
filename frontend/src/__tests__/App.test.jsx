/**
 * Unit tests for App component
 */

// Mock localStorage before any imports
const localStorageMock = {
  getItem: jest.fn(() => null),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
global.localStorage = localStorageMock;

// window.matchMedia is already mocked in setupTests.js which runs before test files
// Mock MSAL library FIRST - must be before msalConfig import
jest.mock('@azure/msal-browser', () => ({
  PublicClientApplication: jest.fn().mockImplementation(() => ({
    initialize: jest.fn(() => Promise.resolve()),
    getAllAccounts: jest.fn(() => []),
    getActiveAccount: jest.fn(() => null),
    handleRedirectPromise: jest.fn(() => Promise.resolve(null)),
  })),
}));

// Mock MSAL config - this will use the mocked PublicClientApplication above
jest.mock('../config/msalConfig', () => {
  const { PublicClientApplication } = require('@azure/msal-browser');
  const mockInstance = new PublicClientApplication({});
  return {
    msalInstance: mockInstance,
  };
});

// Mock auth service
jest.mock('../services/auth', () => ({
  authService: {
    getToken: jest.fn(() => null),
    isTokenExpired: jest.fn(() => false),
    getCurrentUser: jest.fn(() => Promise.resolve(null)),
    logout: jest.fn(),
  },
}));

// Mock MSAL
jest.mock('@azure/msal-react', () => ({
  MsalProvider: ({ children }) => <div data-testid="msal-provider">{children}</div>,
}));

// Mock Google OAuth
jest.mock('@react-oauth/google', () => ({
  GoogleOAuthProvider: ({ children }) => <div data-testid="google-provider">{children}</div>,
}));

// Mock child components to avoid complex dependencies
jest.mock('../components/features/PistaChat', () => {
  return function PistaChat() {
    return <div data-testid="pista-chat">PistaChat</div>;
  };
});

jest.mock('../components/features/Login', () => {
  return function Login() {
    return <div data-testid="login">Login</div>;
  };
});

import React from 'react';
import { render, waitFor } from '@testing-library/react';
import App from '../App';

describe('App Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Ensure matchMedia mock is still set up (in case it was cleared)
    if (!window.matchMedia || typeof window.matchMedia !== 'function') {
      window.matchMedia = function(query) {
        return {
          matches: false,
          media: query,
          onchange: null,
          addListener: jest.fn(),
          removeListener: jest.fn(),
          addEventListener: jest.fn(),
          removeEventListener: jest.fn(),
          dispatchEvent: jest.fn(),
        };
      };
    }
  });

  test('renders without crashing', async () => {
    // App already has its own Router, so don't wrap it again
    render(<App />);

    await waitFor(() => {
      // App should render
      expect(document.body).toBeTruthy();
    });
  });
});
