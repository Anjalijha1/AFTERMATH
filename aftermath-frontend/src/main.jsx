import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import App from './App';
import { AppProvider } from './context/AppContext';
import './index.css';
ReactDOM.createRoot(document.getElementById('root')).render(<React.StrictMode><BrowserRouter><AppProvider><App /><Toaster position="top-right"/></AppProvider></BrowserRouter></React.StrictMode>);
