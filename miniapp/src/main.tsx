import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import { App } from './App';
import { init } from './telegram';
import './styles.css';

init();

createRoot(document.getElementById('root') as HTMLElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
