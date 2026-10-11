import {createRoot} from 'react-dom/client';
import '@fontsource/ibm-plex-sans/latin-400.css';
import '@fontsource/ibm-plex-sans/latin-600.css';
import '@fontsource/ibm-plex-mono/latin-400.css';
import {SimulationApp} from './app';
const initial=new URLSearchParams(location.search).get('run')||'';
createRoot(document.getElementById('root')!).render(<SimulationApp initialRunId={initial}/>);
