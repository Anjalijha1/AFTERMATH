import { Routes, Route } from 'react-router-dom';
import AppLayout from './components/layout/AppLayout';
import Dashboard from './pages/Dashboard';
import Workspaces from './pages/Workspaces';
import Scenarios from './pages/Scenarios';
import CreateScenario from './pages/CreateScenario';
import RunTest from './pages/RunTest';
import RunDetails from './pages/RunDetails';
import RegressionLab from './pages/RegressionLab';
import EvidenceExplorer from './pages/EvidenceExplorer';
import ConsequenceGraphPage from './pages/ConsequenceGraphPage';
import Settings from './pages/Settings';
export default function App() {
    return <Routes><Route element={<AppLayout />}>
 <Route index element={<Dashboard />}/><Route path="workspaces" element={<Workspaces />}/><Route path="scenarios" element={<Scenarios />}/><Route path="scenarios/new" element={<CreateScenario />}/>
 <Route path="run" element={<RunTest />}/><Route path="runs/:id" element={<RunDetails />}/><Route path="regression" element={<RegressionLab />}/><Route path="evidence" element={<EvidenceExplorer />}/>
 <Route path="graph" element={<ConsequenceGraphPage />}/><Route path="settings" element={<Settings />}/></Route></Routes>;
}
