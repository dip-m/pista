/**
 * Unit tests for PistaChat component
 */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import PistaChat from '../PistaChat';

// Mock API
global.fetch = jest.fn();

// Mock config
jest.mock('../../../config/api', () => ({
  API_BASE: 'http://localhost:8000',
}));

// Mock auth service
jest.mock('../../../services/auth', () => ({
  authService: {
    getToken: jest.fn(() => null),
    getAuthHeaders: jest.fn(() => ({})),
    isTokenExpired: jest.fn(() => false),
  },
}));

// Mock msalConfig before any imports
jest.mock('../../../config/msalConfig', () => ({
  msalInstance: {
    initialize: jest.fn(() => Promise.resolve()),
    getAllAccounts: jest.fn(() => []),
    getActiveAccount: jest.fn(() => null),
  },
}));

// Mock anonymous user utils
jest.mock('../../../utils/anonymousUser', () => ({
  hasExceededLimit: jest.fn(() => false),
  incrementMessageCount: jest.fn(),
  getRemainingMessages: jest.fn(() => 5),
}));

// Mock child components
jest.mock('../Marketplace', () => {
  return function Marketplace() {
    return <div data-testid="marketplace">Marketplace</div>;
  };
});

jest.mock('../GameFeaturesEditor', () => {
  return function GameFeaturesEditor() {
    return <div data-testid="game-features-editor">GameFeaturesEditor</div>;
  };
});

jest.mock('../ScoringPad', () => {
  return function ScoringPad() {
    return <div data-testid="scoring-pad">ScoringPad</div>;
  };
});

describe('PistaChat Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ response: 'Test response' }),
    });
  });

  test('renders chat interface', async () => {
    render(
      <BrowserRouter>
        <PistaChat user={null} />
      </BrowserRouter>
    );

    await waitFor(() => {
      // Should render chat container
      const container = document.querySelector('.pista-chat-container');
      expect(container).toBeTruthy();
    });
  });

  test('renders chat interface with user', async () => {
    const mockUser = { id: 1, email: 'test@example.com' };

    render(
      <BrowserRouter>
        <PistaChat user={mockUser} />
      </BrowserRouter>
    );

    await waitFor(() => {
      // Should render chat container
      const container = document.querySelector('.pista-chat-container');
      expect(container).toBeTruthy();
    });
  });
});
