/**
 * Integration tests for chat flow
 */
import React from 'react';
import { render, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import PistaChat from '../../components/features/PistaChat';

// Mock API responses
global.fetch = jest.fn();

// Mock config
jest.mock('../../config/api', () => ({
  API_BASE: 'http://localhost:8000',
}));

// Mock msalConfig before any imports
jest.mock('../../config/msalConfig', () => ({
  msalInstance: {
    initialize: jest.fn(() => Promise.resolve()),
    getAllAccounts: jest.fn(() => []),
    getActiveAccount: jest.fn(() => null),
  },
}));

// Mock auth
jest.mock('../../services/auth', () => ({
  authService: {
    getToken: jest.fn(() => null),
    getAuthHeaders: jest.fn(() => ({})),
    isTokenExpired: jest.fn(() => false),
  },
}));

jest.mock('../../utils/anonymousUser', () => ({
  hasExceededLimit: jest.fn(() => false),
  incrementMessageCount: jest.fn(),
  getRemainingMessages: jest.fn(() => 5),
}));

// Mock child components
jest.mock('../../components/features/Marketplace', () => {
  return function Marketplace() {
    return <div data-testid="marketplace">Marketplace</div>;
  };
});

jest.mock('../../components/features/GameFeaturesEditor', () => {
  return function GameFeaturesEditor() {
    return <div data-testid="game-features-editor">GameFeaturesEditor</div>;
  };
});

jest.mock('../../components/features/ScoringPad', () => {
  return function ScoringPad() {
    return <div data-testid="scoring-pad">ScoringPad</div>;
  };
});

describe('Chat Flow Integration', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    fetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        response: 'Test response',
        suggestions: [],
      }),
    });
  });

  test('chat component renders and initializes', async () => {
    render(
      <BrowserRouter>
        <PistaChat user={null} />
      </BrowserRouter>
    );

    await waitFor(() => {
      // Component should render
      const container = document.querySelector('.pista-chat-container');
      expect(container).toBeTruthy();
    });
  });
});
