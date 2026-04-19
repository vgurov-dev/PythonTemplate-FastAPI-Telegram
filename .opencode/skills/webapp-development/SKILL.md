---
name: webapp-development
description: React + Telegram WebApp SDK development - auth flow, components, TypeScript patterns
license: MIT
compatibility: opencode
metadata:
  audience: frontend-developers
  workflow: webapp
---

# WebApp Development Skill

## Role

Frontend developer building Telegram Web Applications. This skill covers React 18 + Vite + TypeScript + @twa-dev/twa-sdk patterns specific to Telegram Mini Apps.

## Project Structure

```
src/webapp/
├── src/
│   ├── components/        # Reusable UI components
│   │   ├── Button/
│   │   ├── Input/
│   │   └── Layout/
│   ├── pages/             # Route pages
│   │   ├── Home/
│   │   ├── Profile/
│   │   └── Settings/
│   ├── hooks/             # Custom React hooks
│   │   ├── useTelegram.ts
│   │   ├── useAuth.ts
│   │   └── useApi.ts
│   ├── services/          # API clients
│   │   └── api.ts
│   ├── types/             # TypeScript types
│   │   └── index.ts
│   ├── App.tsx
│   └── main.tsx
├── package.json
├── vite.config.ts
└── tsconfig.json
```

## Telegram WebApp SDK

### Initialization

```typescript
// src/webapp/src/main.tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

declare global {
  interface Window {
    Telegram: {
      WebApp: {
        ready: () => void;
        expand: () => void;
        close: () => void;
        initData: string;
        initDataUnsafe: {
          user?: TelegramUser;
          query_id?: string;
          auth_date?: string;
          hash?: string;
        };
        themeParams: ThemeParams;
        colorScheme: 'light' | 'dark';
        platform: string;
      };
    };
  }
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

```typescript
// src/webapp/src/App.tsx
import { useEffect } from 'react';
import { useTelegram } from './hooks/useTelegram';
import Home from './pages/Home/Home';

function App() {
  const { webapp, user } = useTelegram();

  useEffect(() => {
    // Tell Telegram the app is ready
    webapp.ready();

    // Expand to full height
    webapp.expand();
  }, [webapp]);

  return (
    <div className="app" data-color-scheme={webapp.colorScheme}>
      <Home />
    </div>
  );
}

export default App;
```

### TypeScript Types

```typescript
// src/webapp/src/types/index.ts

export interface TelegramUser {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
  language_code?: string;
  is_bot?: boolean;
}

export interface ThemeParams {
  bg_color?: string;
  text_color?: string;
  hint_color?: string;
  link_color?: string;
  button_color?: string;
  button_text_color?: string;
  secondary_bg_color?: string;
}

export interface AuthData {
  user: TelegramUser;
  auth_date: string;
  hash: string;
}

export interface ApiError {
  error: string;
  detail?: string;
}
```

## Custom Hooks

### useTelegram Hook

```typescript
// src/webapp/src/hooks/useTelegram.ts
import { useMemo } from 'react';
import type { TelegramUser, ThemeParams } from '../types';

interface UseTelegramReturn {
  webapp: typeof window.Telegram.WebApp;
  user: TelegramUser | null;
  colorScheme: 'light' | 'dark';
  themeParams: ThemeParams;
  expand: () => void;
  close: () => void;
}

export function useTelegram(): UseTelegramReturn {
  const webapp = window.Telegram.WebApp;

  const user = useMemo(() => {
    return webapp.initDataUnsafe.user ?? null;
  }, [webapp.initDataUnsafe.user]);

  return {
    webapp,
    user,
    colorScheme: webapp.colorScheme,
    themeParams: webapp.themeParams,
    expand: () => webapp.expand(),
    close: () => webapp.close(),
  };
}
```

### useAuth Hook (Backend Validation)

```typescript
// src/webapp/src/hooks/useAuth.ts
import { useState, useEffect, useCallback } from 'react';
import { validateAuthData, exchangeToken } from '../services/api';
import type { TelegramUser } from '../types';

interface UseAuthReturn {
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  user: TelegramUser | null;
  token: string | null;
  login: () => Promise<void>;
  logout: () => void;
}

export function useAuth(): UseAuthReturn {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [user, setUser] = useState<TelegramUser | null>(null);
  const [token, setToken] = useState<string | null>(null);

  const login = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const webapp = window.Telegram.WebApp;

      // Validate initData with backend
      const authResult = await validateAuthData({
        initData: webapp.initData,
        user: webapp.initDataUnsafe.user,
      });

      if (authResult.success) {
        setToken(authResult.token);
        setUser(authResult.user);
        setIsAuthenticated(true);

        // Store token securely
        sessionStorage.setItem('auth_token', authResult.token);
      } else {
        setError('Authentication failed');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    setIsAuthenticated(false);
    sessionStorage.removeItem('auth_token');
  }, []);

  // Auto-login on mount
  useEffect(() => {
    const storedToken = sessionStorage.getItem('auth_token');
    if (storedToken) {
      setToken(storedToken);
      setIsAuthenticated(true);
      setIsLoading(false);
    } else {
      setIsLoading(false);
    }
  }, []);

  return {
    isAuthenticated,
    isLoading,
    error,
    user,
    token,
    login,
    logout,
  };
}
```

### useApi Hook

```typescript
// src/webapp/src/hooks/useApi.ts
import { useState, useCallback } from 'react';
import { apiClient } from '../services/api';
import type { ApiError } from '../types';

interface UseApiOptions<T> {
  onSuccess?: (data: T) => void;
  onError?: (error: ApiError) => void;
}

interface UseApiReturn<T> {
  data: T | null;
  isLoading: boolean;
  error: ApiError | null;
  execute: (body?: unknown) => Promise<T | null>;
  reset: () => void;
}

export function useApi<T>(
  endpoint: string,
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' = 'GET',
  options?: UseApiOptions<T>
): UseApiReturn<T> {
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  const execute = useCallback(async (body?: unknown) => {
    setIsLoading(true);
    setError(null);

    try {
      const result = await apiClient.request<T>({
        endpoint,
        method,
        body,
      });

      setData(result);
      options?.onSuccess?.(result);
      return result;
    } catch (err) {
      const apiError = err as ApiError;
      setError(apiError);
      options?.onError?.(apiError);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, [endpoint, method, options]);

  const reset = useCallback(() => {
    setData(null);
    setError(null);
    setIsLoading(false);
  }, []);

  return { data, isLoading, error, execute, reset };
}
```

## API Client

```typescript
// src/webapp/src/services/api.ts
import type { TelegramUser, ApiError } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface RequestOptions {
  endpoint: string;
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  body?: unknown;
  headers?: Record<string, string>;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private getAuthHeaders(): Record<string, string> {
    const token = sessionStorage.getItem('auth_token');
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  async request<T>(options: RequestOptions): Promise<T> {
    const { endpoint, method = 'GET', body, headers = {} } = options;

    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...this.getAuthHeaders(),
        ...headers,
      },
      body: body ? JSON.stringify(body) : undefined,
    });

    if (!response.ok) {
      const error: ApiError = await response.json().catch(() => ({
        error: `HTTP ${response.status}`,
        detail: response.statusText,
      }));
      throw error;
    }

    return response.json();
  }
}

export const apiClient = new ApiClient(API_BASE_URL);

// Auth endpoints
export async function validateAuthData(data: {
  initData: string;
  user?: TelegramUser;
}): Promise<{ success: boolean; token?: string; user?: TelegramUser }> {
  return apiClient.request({
    endpoint: '/api/auth/validate',
    method: 'POST',
    body: data,
  });
}

export async function exchangeToken(token: string): Promise<{
  access_token: string;
  refresh_token: string;
}> {
  return apiClient.request({
    endpoint: '/api/auth/exchange',
    method: 'POST',
    body: { token },
  });
}
```

## Components

### Button Component

```typescript
// src/webapp/src/components/Button/Button.tsx
import { ReactNode, CSSProperties } from 'react';

interface ButtonProps {
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  variant?: 'primary' | 'secondary' | 'danger';
  size?: 'small' | 'medium' | 'large';
  fullWidth?: boolean;
  className?: string;
}

export function Button({
  children,
  onClick,
  disabled = false,
  variant = 'primary',
  size = 'medium',
  fullWidth = false,
  className = '',
}: ButtonProps) {
  const baseStyles: CSSProperties = {
    borderRadius: '8px',
    fontWeight: 500,
    cursor: disabled ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.5 : 1,
    transition: 'opacity 0.2s',
    width: fullWidth ? '100%' : 'auto',
  };

  const variantStyles: Record<string, CSSProperties> = {
    primary: {
      backgroundColor: '#3390ec',
      color: '#ffffff',
    },
    secondary: {
      backgroundColor: '#e5e5ea',
      color: '#000000',
    },
    danger: {
      backgroundColor: '#ff3b30',
      color: '#ffffff',
    },
  };

  const sizeStyles: Record<string, CSSProperties> = {
    small: { padding: '6px 12px', fontSize: '14px' },
    medium: { padding: '10px 20px', fontSize: '16px' },
    large: { padding: '14px 28px', fontSize: '18px' },
  };

  const style: CSSProperties = {
    ...baseStyles,
    ...variantStyles[variant],
    ...sizeStyles[size],
  };

  return (
    <button
      style={style}
      onClick={onClick}
      disabled={disabled}
      className={className}
    >
      {children}
    </button>
  );
}
```

### MainButton (Telegram SDK)

```typescript
// src/webapp/src/components/MainButton/MainButton.tsx
import { useEffect, useState } from 'react';

interface MainButtonProps {
  text: string;
  onClick: () => void;
  disabled?: boolean;
  loading?: boolean;
}

export function MainButton({
  text,
  onClick,
  disabled = false,
  loading = false,
}: MainButtonProps) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const webapp = window.Telegram.WebApp;

    webapp.MainButton.setText(text);
    webapp.MainButton.onClick(onClick);
    webapp.MainButton.show();
    setVisible(true);

    return () => {
      webapp.MainButton.offClick(onClick);
      webapp.MainButton.hide();
    };
  }, [text, onClick]);

  useEffect(() => {
    const webapp = window.Telegram.WebApp;

    if (disabled) {
      webapp.MainButton.disable();
    } else {
      webapp.MainButton.enable();
    }
  }, [disabled]);

  useEffect(() => {
    const webapp = window.Telegram.WebApp;

    if (loading) {
      webapp.MainButton.showProgress();
    } else {
      webapp.MainButton.hideProgress();
    }
  }, [loading]);

  return null; // MainButton is rendered by Telegram SDK
}
```

## Pages

### Home Page

```typescript
// src/webapp/src/pages/Home/Home.tsx
import { useApi } from '../../hooks/useApi';
import { Button } from '../../components/Button/Button';
import { useTelegram } from '../../hooks/useTelegram';

interface Profile {
  id: number;
  username: string;
  first_name: string;
  balance: number;
}

export default function Home() {
  const { user } = useTelegram();
  const { data, isLoading, error, execute } = useApi<Profile>('/api/users/me');
  const [refreshing, setRefreshing] = useState(false);

  const handleRefresh = async () => {
    setRefreshing(true);
    await execute();
    setRefreshing(false);
  };

  return (
    <div className="page home">
      <header className="header">
        <h1>Добро пожаловать, {user?.first_name}!</h1>
        {user?.username && <span>@{user.username}</span>}
      </header>

      <main className="content">
        {isLoading && <div className="loading">Загрузка...</div>}

        {error && (
          <div className="error">
            <p>Ошибка: {error.error}</p>
            <Button onClick={handleRefresh}>Повторить</Button>
          </div>
        )}

        {data && (
          <div className="profile-card">
            <h2>Профиль</h2>
            <p>ID: {data.id}</p>
            <p>Имя: {data.first_name}</p>
            <p>Баланс: {data.balance} ₽</p>
          </div>
        )}
      </main>
    </div>
  );
}
```

## Theming

```typescript
// src/webapp/src/styles/theme.ts
import { CSSProperties } from 'react';
import type { ThemeParams } from '../types';

export function getThemeStyles(themeParams: ThemeParams): Record<string, CSSProperties> {
  return {
    '--bg-color': themeParams.bg_color || '#ffffff',
    '--text-color': themeParams.text_color || '#000000',
    '--hint-color': themeParams.hint_color || '#999999',
    '--link-color': themeParams.link_color || '#3390ec',
    '--button-color': themeParams.button_color || '#3390ec',
    '--button-text-color': themeParams.button_text_color || '#ffffff',
    '--secondary-bg-color': themeParams.secondary_bg_color || '#f0f0f0',
  };
}

// src/webapp/src/index.css
:root {
  --bg-color: #ffffff;
  --text-color: #000000;
  --hint-color: #999999;
  --link-color: #3390ec;
  --button-color: #3390ec;
  --button-text-color: #ffffff;
  --secondary-bg-color: #f0f0f0;
}

[data-color-scheme="dark"] {
  --bg-color: #17212b;
  --text-color: #ffffff;
  --hint-color: #6c7e8c;
  --link-color: #6cb4f5;
  --button-color: #3390ec;
  --button-text-color: #ffffff;
  --secondary-bg-color: #1e2a36;
}

body {
  background-color: var(--bg-color);
  color: var(--text-color);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  margin: 0;
  padding: 0;
}
```

## Vite Configuration

```typescript
// src/webapp/vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
});
```

## Environment Variables

```bash
# .env.example for webapp
VITE_API_URL=http://localhost:8000
VITE_APP_NAME=my-telegram-app
```

```typescript
// src/webapp/src/vite-env.d.ts
/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string;
  readonly VITE_APP_NAME: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
```

## Anti-Patterns (NEVER do)

| Anti-pattern | Problem | Solution |
|-------------|---------|----------|
| Hardcode API URL | Inflexible | Use environment variable |
| No auth validation | Anyone can access | Validate initData with backend |
| Store token in localStorage | XSS vulnerability | Use sessionStorage or memory |
| Ignore colorScheme | Dark mode broken | Use themeParams |
| Direct Telegram API calls | Duplication | Use useTelegram hook |
| No error boundaries | App crashes | Wrap with ErrorBoundary |
| Fetch without abort | Memory leak | Use AbortController |

## Testing

```typescript
// src/webapp/tests/hooks/useTelegram.test.ts
import { renderHook, act } from '@testing-library/react';
import { useTelegram } from '../../hooks/useTelegram';

// Mock Telegram WebApp
beforeEach(() => {
  (window as any).Telegram = {
    WebApp: {
      ready: jest.fn(),
      expand: jest.fn(),
      close: jest.fn(),
      initData: 'test_init_data',
      initDataUnsafe: {
        user: {
          id: 123,
          first_name: 'Test',
          last_name: 'User',
          username: 'testuser',
        },
      },
      themeParams: {
        bg_color: '#ffffff',
        text_color: '#000000',
      },
      colorScheme: 'light',
      platform: 'android',
    },
  };
});

test('useTelegram returns webapp instance', () => {
  const { result } = renderHook(() => useTelegram());

  expect(result.current.webapp).toBeDefined();
  expect(result.current.webapp.ready).toBeDefined();
  expect(result.current.user?.id).toBe(123);
});
```

## Checklist

Before deploying webapp:

- [ ] initData is validated by backend
- [ ] Token stored in sessionStorage, not localStorage
- [ ] Dark/light mode using themeParams
- [ ] All API calls include auth headers
- [ ] Error boundaries wrap components
- [ ] Environment variables for API URL
- [ ] Telegram SDK methods called (ready, expand)
- [ ] TypeScript strict mode enabled
- [ ] Build produces optimized bundle
