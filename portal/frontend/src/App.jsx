import { Navigate, Route, Routes } from 'react-router-dom'
import GlobalSearch from './components/GlobalSearch.jsx'
import Sidebar from './components/Sidebar.jsx'
import { FilterProvider } from './context/FilterContext.jsx'
import CompliancePage from './pages/CompliancePage.jsx'
import DevicesPage from './pages/DevicesPage.jsx'
import NonCompliancePage from './pages/NonCompliancePage.jsx'

export default function App() {
  return (
    <FilterProvider>
      <div className="shell">
        <Sidebar />
        <main className="content">
          <GlobalSearch />
          <Routes>
            <Route path="/" element={<Navigate to="/devices" replace />} />
            <Route path="/devices" element={<DevicesPage />} />
            <Route path="/non-compliance" element={<NonCompliancePage />} />
            <Route path="/compliance" element={<CompliancePage />} />
            <Route path="*" element={<Navigate to="/devices" replace />} />
          </Routes>
        </main>
      </div>
    </FilterProvider>
  )
}
