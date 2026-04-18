import type { ThemeParams } from '@twa-dev/twa-sdk/types';

declare global {
  interface Window {
    Telegram: {
      WebApp: {
        ready: () => void;
        expand: () => void;
        close: () => void;
        themeParams: ThemeParams;
        colorScheme: 'light' | 'dark';
        platform: string;
      };
    };
  }
}

function App() {
  return <div>Hello Telegram Web App!</div>;
}

export default App;