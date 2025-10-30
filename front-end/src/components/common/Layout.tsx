import { useState } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import {
  Box,
  Drawer,
  AppBar,
  Toolbar,
  List,
  Typography,
  Divider,
  IconButton,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Avatar,
  Menu,
  MenuItem,
  Badge,
  Chip,
} from '@mui/material'
import {
  Menu as MenuIcon,
  ChevronLeft as ChevronLeftIcon,
  Storage as StorageIcon,
  Comment as CommentIcon,
  CheckCircle as ApprovalIcon,
  Person as PersonIcon,
  Logout as LogoutIcon,
  Home as HomeIcon,
  History as HistoryIcon,
  PlayArrow as ApplyIcon,
} from '@mui/icons-material'
import { RootState, AppDispatch } from '../../store/store'
import { logout } from '../../store/authSlice'

const drawerWidth = 240

export default function Layout() {
  const [open, setOpen] = useState(true)
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null)
  const navigate = useNavigate()
  const location = useLocation()
  const dispatch = useDispatch<AppDispatch>()
  const { user } = useSelector((state: RootState) => state.auth)
  const { pendingApprovals } = useSelector((state: RootState) => state.comments)

  const handleDrawerToggle = () => {
    setOpen(!open)
  }

  const handleProfileMenu = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget)
  }

  const handleCloseMenu = () => {
    setAnchorEl(null)
  }

  const handleLogout = async () => {
    await dispatch(logout())
    navigate('/login')
  }

  const menuItems = [
    {
      text: 'Home',
      icon: <HomeIcon />,
      path: '/',
      roles: ['suggest_only', 'approver', 'admin'],
    },
    {
      text: 'Catalog Explorer',
      icon: <StorageIcon />,
      path: '/catalog',
      roles: ['suggest_only', 'approver', 'admin'],
    },
    {
      text: 'My Comments',
      icon: <CommentIcon />,
      path: '/my-comments',
      roles: ['suggest_only', 'approver', 'admin'],
    },
    {
      text: 'Approval Queue',
      icon: <ApprovalIcon />,
      path: '/approvals',
      roles: ['approver', 'admin'],
      badge: pendingApprovals.length,
    },
    {
      text: 'Apply Queue',
      icon: <ApplyIcon />,
      path: '/apply-queue',
      roles: ['approver', 'admin'],
    },
    {
      text: 'Audit Log',
      icon: <HistoryIcon />,
      path: '/audit-log',
      roles: ['approver', 'admin'],
    },
  ]

  const getRoleColor = () => {
    switch (user?.role) {
      case 'admin':
        return 'error'
      case 'approver':
        return 'success'
      case 'suggest_only':
        return 'primary'
      default:
        return 'default'
    }
  }

  return (
    <Box sx={{ display: 'flex', width: '100%' }}>
      <AppBar
        position="fixed"
        sx={{
          width: `calc(100% - ${open ? drawerWidth : 0}px)`,
          ml: `${open ? drawerWidth : 0}px`,
          transition: (theme) =>
            theme.transitions.create(['margin', 'width'], {
              easing: theme.transitions.easing.sharp,
              duration: theme.transitions.duration.leavingScreen,
            }),
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="toggle drawer"
            onClick={handleDrawerToggle}
            edge="start"
            sx={{ mr: 2 }}
          >
            {open ? <ChevronLeftIcon /> : <MenuIcon />}
          </IconButton>
          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
            Databricks Metadata Manager
          </Typography>
          {user && (
            <Box display="flex" alignItems="center" gap={2}>
              <Chip
                label={user.role.replace('_', ' ').toUpperCase()}
                size="small"
                color={getRoleColor() as any}
                sx={{ color: 'white' }}
              />
              <IconButton onClick={handleProfileMenu} color="inherit" data-testid="user-profile">
                <Avatar sx={{ width: 32, height: 32 }}>
                  {user.full_name?.[0] || user.username[0].toUpperCase()}
                </Avatar>
              </IconButton>
            </Box>
          )}
          <Menu
            anchorEl={anchorEl}
            open={Boolean(anchorEl)}
            onClose={handleCloseMenu}
            anchorOrigin={{
              vertical: 'bottom',
              horizontal: 'right',
            }}
            transformOrigin={{
              vertical: 'top',
              horizontal: 'right',
            }}
          >
            <MenuItem onClick={() => { navigate('/profile'); handleCloseMenu() }}>
              <ListItemIcon>
                <PersonIcon fontSize="small" />
              </ListItemIcon>
              Profile
            </MenuItem>
            <Divider />
            <MenuItem onClick={handleLogout}>
              <ListItemIcon>
                <LogoutIcon fontSize="small" />
              </ListItemIcon>
              Logout
            </MenuItem>
          </Menu>
        </Toolbar>
      </AppBar>
      <Drawer
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: drawerWidth,
            boxSizing: 'border-box',
          },
        }}
        variant="persistent"
        anchor="left"
        open={open}
      >
        <Toolbar />
        <Divider />
        <List>
          {menuItems
            .filter((item) => user && item.roles.includes(user.role))
            .map((item) => (
              <ListItem key={item.text} disablePadding>
                <ListItemButton
                  selected={location.pathname === item.path}
                  onClick={() => navigate(item.path)}
                  data-testid={`nav-${item.text.toLowerCase().replace(/\s+/g, '-')}`}
                >
                  <ListItemIcon>
                    {item.badge ? (
                      <Badge badgeContent={item.badge} color="error">
                        {item.icon}
                      </Badge>
                    ) : (
                      item.icon
                    )}
                  </ListItemIcon>
                  <ListItemText primary={item.text} />
                </ListItemButton>
              </ListItem>
            ))}
        </List>
      </Drawer>
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          bgcolor: 'background.default',
          p: 3,
          width: `calc(100% - ${open ? drawerWidth : 0}px)`,
          ml: open ? 0 : `-${drawerWidth}px`,
          transition: (theme) =>
            theme.transitions.create(['margin', 'width'], {
              easing: theme.transitions.easing.sharp,
              duration: theme.transitions.duration.leavingScreen,
            }),
        }}
      >
        <Toolbar />
        <Outlet />
      </Box>
    </Box>
  )
}