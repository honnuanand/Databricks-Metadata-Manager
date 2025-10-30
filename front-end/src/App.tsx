import { useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import { Box } from '@mui/material'
import { RootState, AppDispatch } from './store/store'
import { getCurrentUser } from './store/authSlice'
import Layout from './components/common/Layout'
import Login from './pages/Login'
import Home from './pages/Home'
import CatalogExplorer from './pages/CatalogExplorer'
import ApprovalQueue from './pages/ApprovalQueue'
import MyComments from './pages/MyComments'
import UserProfile from './pages/UserProfile'
import AuditLog from './pages/AuditLog'
import ApplyQueue from './pages/ApplyQueue'
import DevUserSwitcher from './components/common/DevUserSwitcher'
import TestRunner from './testing/TestRunner'

function App() {
  const dispatch = useDispatch<AppDispatch>()
  const { isAuthenticated } = useSelector((state: RootState) => state.auth)
  const isDev = import.meta.env.DEV

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (token && !isAuthenticated) {
      dispatch(getCurrentUser())
    }
  }, [dispatch, isAuthenticated])

  return (
    <Box sx={{ display: 'flex', height: '100vh' }}>
      {isDev && <DevUserSwitcher />}
      <Routes>
        <Route path="/login" element={!isAuthenticated ? <Login /> : <Navigate to="/" />} />
        {/* Test Runner - accessible without full authentication (inside SSO boundary) */}
        <Route path="/test-runner" element={<TestRunner />} />
        <Route
          path="/"
          element={isAuthenticated ? <Layout /> : <Navigate to="/login" />}
        >
          <Route index element={<Home />} />
          <Route path="catalog" element={<CatalogExplorer />} />
          <Route path="approvals" element={<ApprovalQueue />} />
          <Route path="my-comments" element={<MyComments />} />
          <Route path="apply-queue" element={<ApplyQueue />} />
          <Route path="audit-log" element={<AuditLog />} />
          <Route path="profile" element={<UserProfile />} />
        </Route>
      </Routes>
    </Box>
  )
}

export default App