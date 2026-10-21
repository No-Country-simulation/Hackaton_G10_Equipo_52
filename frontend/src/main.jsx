// Punto de entrada: monta la app dentro de <div id="root"> (index.html)
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { SesionProvider } from './context/SesionContext';
import App from './App';
import ErrorBoundary from './components/ErrorBoundary';
import './styles/global.css';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ErrorBoundary>
      <SesionProvider>
        <App />
      </SesionProvider>
    </ErrorBoundary>
  </StrictMode>,
);