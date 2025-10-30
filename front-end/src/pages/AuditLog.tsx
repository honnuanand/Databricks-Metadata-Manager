import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  TextField,
  InputAdornment,
  Chip,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Grid,
  Card,
  CardContent,
  IconButton,
  Tooltip,
  Alert,
  CircularProgress,
} from '@mui/material';
import {
  Search as SearchIcon,
  FilterList as FilterIcon,
  History as HistoryIcon,
  CheckCircle as ApprovedIcon,
  Cancel as RejectedIcon,
  Schedule as PendingIcon,
  PlayArrow as AppliedIcon,
  Edit as DraftIcon,
  Visibility as ViewIcon,
} from '@mui/icons-material';
import { commentService } from '../services/comment.service';

interface Comment {
  id: string;
  entity_type: 'catalog' | 'schema' | 'table' | 'column';
  entity_catalog: string;
  entity_schema: string;
  entity_table: string;
  entity_column?: string;
  entity_path: string;
  current_comment: string | null;
  suggested_comment: string;
  status: 'draft' | 'pending' | 'approved' | 'rejected' | 'applied';
  created_by: string;
  created_by_role?: string;
  created_at: string;
  updated_at?: string;
  approved_by?: string;
  approved_by_role?: string;
  approved_at?: string;
  rejected_by?: string;
  rejected_at?: string;
  applied_by?: string;
  applied_by_role?: string;
  applied_at?: string;
  review_feedback?: string;
}

const AuditLog: React.FC = () => {
  const [comments, setComments] = useState<Comment[]>([]);
  const [filteredComments, setFilteredComments] = useState<Comment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Pagination
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);

  // Filters
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [entityTypeFilter, setEntityTypeFilter] = useState<string>('all');
  const [userFilter, setUserFilter] = useState('');

  // Load all comments
  useEffect(() => {
    const fetchAllComments = async () => {
      try {
        setLoading(true);
        const data = await commentService.getAllComments();
        setComments(data);
        setFilteredComments(data);
      } catch (err) {
        console.error('Error fetching comments:', err);
        setError('Failed to load audit log');
      } finally {
        setLoading(false);
      }
    };

    fetchAllComments();
  }, []);

  // Apply filters
  useEffect(() => {
    let filtered = [...comments];

    // Search filter
    if (searchTerm) {
      filtered = filtered.filter(comment =>
        comment.entity_path.toLowerCase().includes(searchTerm.toLowerCase()) ||
        comment.suggested_comment.toLowerCase().includes(searchTerm.toLowerCase()) ||
        comment.created_by.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (comment.current_comment && comment.current_comment.toLowerCase().includes(searchTerm.toLowerCase()))
      );
    }

    // Status filter
    if (statusFilter !== 'all') {
      filtered = filtered.filter(comment => comment.status === statusFilter);
    }

    // Entity type filter
    if (entityTypeFilter !== 'all') {
      filtered = filtered.filter(comment => comment.entity_type === entityTypeFilter);
    }

    // User filter
    if (userFilter) {
      filtered = filtered.filter(comment =>
        comment.created_by.toLowerCase().includes(userFilter.toLowerCase()) ||
        (comment.approved_by && comment.approved_by.toLowerCase().includes(userFilter.toLowerCase())) ||
        (comment.rejected_by && comment.rejected_by.toLowerCase().includes(userFilter.toLowerCase())) ||
        (comment.applied_by && comment.applied_by.toLowerCase().includes(userFilter.toLowerCase()))
      );
    }

    setFilteredComments(filtered);
    setPage(0); // Reset to first page when filters change
  }, [searchTerm, statusFilter, entityTypeFilter, userFilter, comments]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'draft':
        return 'default';
      case 'pending':
        return 'warning';
      case 'approved':
        return 'success';
      case 'rejected':
        return 'error';
      case 'applied':
        return 'info';
      default:
        return 'default';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'draft':
        return <DraftIcon fontSize="small" />;
      case 'pending':
        return <PendingIcon fontSize="small" />;
      case 'approved':
        return <ApprovedIcon fontSize="small" />;
      case 'rejected':
        return <RejectedIcon fontSize="small" />;
      case 'applied':
        return <AppliedIcon fontSize="small" />;
      default:
        return null;
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const getRoleChipColor = (role?: string) => {
    switch (role) {
      case 'admin':
        return 'error';
      case 'approver':
        return 'success';
      case 'suggest_only':
        return 'primary';
      default:
        return 'default';
    }
  };

  const formatRoleLabel = (role?: string) => {
    if (!role) return '';
    return role.replace('_', ' ').toUpperCase();
  };

  // Statistics
  const stats = {
    total: comments.length,
    draft: comments.filter(c => c.status === 'draft').length,
    pending: comments.filter(c => c.status === 'pending').length,
    approved: comments.filter(c => c.status === 'approved').length,
    rejected: comments.filter(c => c.status === 'rejected').length,
    applied: comments.filter(c => c.status === 'applied').length,
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      {/* Header */}
      <Box mb={3}>
        <Box display="flex" alignItems="center" gap={2} mb={2}>
          <HistoryIcon fontSize="large" color="primary" />
          <Typography variant="h4">Audit Log</Typography>
        </Box>
        <Typography variant="body1" color="text.secondary">
          View and search all metadata change requests across your catalogs
        </Typography>
      </Box>

      {/* Statistics Cards */}
      <Grid container spacing={2} mb={3}>
        <Grid item xs={12} sm={6} md={2}>
          <Card>
            <CardContent>
              <Typography variant="h4">{stats.total}</Typography>
              <Typography variant="body2" color="text.secondary">Total Changes</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={2}>
          <Card>
            <CardContent>
              <Typography variant="h4" color="text.secondary">{stats.draft}</Typography>
              <Typography variant="body2" color="text.secondary">Draft</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={2}>
          <Card>
            <CardContent>
              <Typography variant="h4" color="warning.main">{stats.pending}</Typography>
              <Typography variant="body2" color="text.secondary">Pending</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={2}>
          <Card>
            <CardContent>
              <Typography variant="h4" color="success.main">{stats.approved}</Typography>
              <Typography variant="body2" color="text.secondary">Approved</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={2}>
          <Card>
            <CardContent>
              <Typography variant="h4" color="error.main">{stats.rejected}</Typography>
              <Typography variant="body2" color="text.secondary">Rejected</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={2}>
          <Card>
            <CardContent>
              <Typography variant="h4" color="info.main">{stats.applied}</Typography>
              <Typography variant="body2" color="text.secondary">Applied</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* Filters */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={2}>
          <Grid item xs={12} md={4}>
            <TextField
              fullWidth
              size="small"
              placeholder="Search by path, comment, or user..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon />
                  </InputAdornment>
                ),
              }}
            />
          </Grid>
          <Grid item xs={12} sm={6} md={2}>
            <FormControl fullWidth size="small">
              <InputLabel>Status</InputLabel>
              <Select
                value={statusFilter}
                label="Status"
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <MenuItem value="all">All Statuses</MenuItem>
                <MenuItem value="draft">Draft</MenuItem>
                <MenuItem value="pending">Pending</MenuItem>
                <MenuItem value="approved">Approved</MenuItem>
                <MenuItem value="rejected">Rejected</MenuItem>
                <MenuItem value="applied">Applied</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={6} md={2}>
            <FormControl fullWidth size="small">
              <InputLabel>Entity Type</InputLabel>
              <Select
                value={entityTypeFilter}
                label="Entity Type"
                onChange={(e) => setEntityTypeFilter(e.target.value)}
              >
                <MenuItem value="all">All Types</MenuItem>
                <MenuItem value="column">Column</MenuItem>
                <MenuItem value="table">Table</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} md={4}>
            <TextField
              fullWidth
              size="small"
              placeholder="Filter by user..."
              value={userFilter}
              onChange={(e) => setUserFilter(e.target.value)}
            />
          </Grid>
        </Grid>
      </Paper>

      {/* Results Table */}
      <Paper>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Status</TableCell>
                <TableCell>Entity</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>Suggested Comment</TableCell>
                <TableCell>Created By</TableCell>
                <TableCell>Created At</TableCell>
                <TableCell>Last Updated</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredComments
                .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
                .map((comment) => (
                  <TableRow key={comment.id} hover>
                    <TableCell>
                      <Chip
                        icon={getStatusIcon(comment.status)}
                        label={comment.status.toUpperCase()}
                        color={getStatusColor(comment.status) as any}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" fontFamily="monospace">
                        {comment.entity_path}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={comment.entity_type}
                        size="small"
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell sx={{ maxWidth: 300 }}>
                      <Typography variant="body2" noWrap>
                        {comment.suggested_comment}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Box display="flex" alignItems="center" gap={1} mb={0.5}>
                        <Typography variant="body2">{comment.created_by}</Typography>
                        {comment.created_by_role && (
                          <Chip
                            label={formatRoleLabel(comment.created_by_role)}
                            size="small"
                            color={getRoleChipColor(comment.created_by_role) as any}
                            sx={{ height: 18, fontSize: '0.65rem' }}
                          />
                        )}
                      </Box>
                      {comment.approved_by && (
                        <Box display="flex" alignItems="center" gap={1}>
                          <Typography variant="caption" color="success.main">
                            Approved by: {comment.approved_by}
                          </Typography>
                          {comment.approved_by_role && (
                            <Chip
                              label={formatRoleLabel(comment.approved_by_role)}
                              size="small"
                              color={getRoleChipColor(comment.approved_by_role) as any}
                              sx={{ height: 16, fontSize: '0.6rem' }}
                            />
                          )}
                        </Box>
                      )}
                      {comment.rejected_by && (
                        <Box display="flex" alignItems="center" gap={1}>
                          <Typography variant="caption" color="error.main">
                            Rejected by: {comment.rejected_by}
                          </Typography>
                          {comment.rejected_at && (
                            <Chip
                              label={formatRoleLabel(comment.rejected_by)}
                              size="small"
                              color="default"
                              sx={{ height: 16, fontSize: '0.6rem' }}
                            />
                          )}
                        </Box>
                      )}
                      {comment.applied_by && (
                        <Box display="flex" alignItems="center" gap={1}>
                          <Typography variant="caption" color="info.main">
                            Applied by: {comment.applied_by}
                          </Typography>
                          {comment.applied_by_role && (
                            <Chip
                              label={formatRoleLabel(comment.applied_by_role)}
                              size="small"
                              color={getRoleChipColor(comment.applied_by_role) as any}
                              sx={{ height: 16, fontSize: '0.6rem' }}
                            />
                          )}
                        </Box>
                      )}
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">{formatDate(comment.created_at)}</Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        {comment.updated_at ? formatDate(comment.updated_at) : '-'}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Tooltip title="View Details">
                        <IconButton size="small">
                          <ViewIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                ))}
            </TableBody>
          </Table>
        </TableContainer>

        <TablePagination
          component="div"
          count={filteredComments.length}
          page={page}
          onPageChange={(_, newPage) => setPage(newPage)}
          rowsPerPage={rowsPerPage}
          onRowsPerPageChange={(e) => {
            setRowsPerPage(parseInt(e.target.value, 10));
            setPage(0);
          }}
          rowsPerPageOptions={[10, 25, 50, 100]}
        />
      </Paper>
    </Box>
  );
};

export default AuditLog;