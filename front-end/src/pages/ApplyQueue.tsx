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
  Checkbox,
  Button,
  Chip,
  Alert,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import {
  PlayArrow as ApplyIcon,
  CheckCircle as ApprovedIcon,
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
  status: string;
  created_by: string;
  created_at: string;
  approved_by?: string;
  approved_at?: string;
  review_feedback?: string;
}

const ApplyQueue: React.FC = () => {
  const [approvedComments, setApprovedComments] = useState<Comment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Pagination
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);

  // Selection
  const [selected, setSelected] = useState<string[]>([]);

  // Applying
  const [applying, setApplying] = useState(false);
  const [applyDialog, setApplyDialog] = useState(false);
  const [selectedComment, setSelectedComment] = useState<Comment | null>(null);

  // Load approved comments
  useEffect(() => {
    fetchApprovedComments();
  }, []);

  const fetchApprovedComments = async () => {
    try {
      setLoading(true);
      setError(null);
      const allComments = await commentService.getAllComments();
      // Filter for approved status only
      const approved = allComments.filter(c => c.status === 'approved');
      setApprovedComments(approved);
    } catch (err) {
      console.error('Error fetching approved comments:', err);
      setError('Failed to load approved comments');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectAll = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.checked) {
      setSelected(approvedComments.map(c => c.id));
    } else {
      setSelected([]);
    }
  };

  const handleSelect = (id: string) => {
    const selectedIndex = selected.indexOf(id);
    let newSelected: string[] = [];

    if (selectedIndex === -1) {
      newSelected = [...selected, id];
    } else {
      newSelected = selected.filter(s => s !== id);
    }

    setSelected(newSelected);
  };

  const handleApplyComment = async (comment: Comment) => {
    setSelectedComment(comment);
    setApplyDialog(true);
  };

  const confirmApply = async () => {
    if (!selectedComment) return;

    try {
      setApplying(true);
      setError(null);
      await commentService.applyComment(selectedComment.id);
      setSuccess(`Successfully applied comment to ${selectedComment.entity_path}`);
      setApplyDialog(false);
      setSelectedComment(null);
      // Refresh the list
      await fetchApprovedComments();
    } catch (err) {
      console.error('Error applying comment:', err);
      setError('Failed to apply comment to Databricks');
    } finally {
      setApplying(false);
    }
  };

  const handleBatchApply = async () => {
    if (selected.length === 0) return;

    try {
      setApplying(true);
      setError(null);

      // Apply each selected comment
      for (const id of selected) {
        await commentService.applyComment(id);
      }

      setSuccess(`Successfully applied ${selected.length} comment(s) to Databricks`);
      setSelected([]);
      // Refresh the list
      await fetchApprovedComments();
    } catch (err) {
      console.error('Error batch applying comments:', err);
      setError('Failed to apply some comments to Databricks');
    } finally {
      setApplying(false);
    }
  };

  const isSelected = (id: string) => selected.indexOf(id) !== -1;

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
        <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
          <Box>
            <Typography variant="h4">Apply Queue</Typography>
            <Typography variant="body2" color="text.secondary" mt={1}>
              Apply approved metadata changes to Databricks
            </Typography>
          </Box>
          {selected.length > 0 && (
            <Box display="flex" gap={2} alignItems="center">
              <Typography variant="body2" color="text.secondary">
                {selected.length} selected
              </Typography>
              <Button
                variant="contained"
                color="primary"
                startIcon={<ApplyIcon />}
                onClick={handleBatchApply}
                disabled={applying}
              >
                Apply Selected ({selected.length})
              </Button>
            </Box>
          )}
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 3 }} onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}

      {approvedComments.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <ApprovedIcon sx={{ fontSize: 60, color: 'text.disabled', mb: 2 }} />
          <Typography variant="h6" color="text.secondary">
            No approved comments ready to apply
          </Typography>
          <Typography variant="body2" color="text.secondary" mt={1}>
            Comments will appear here after they've been approved
          </Typography>
        </Paper>
      ) : (
        <Paper>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell padding="checkbox">
                    <Checkbox
                      indeterminate={selected.length > 0 && selected.length < approvedComments.length}
                      checked={approvedComments.length > 0 && selected.length === approvedComments.length}
                      onChange={handleSelectAll}
                    />
                  </TableCell>
                  <TableCell>Entity</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell>Current Comment</TableCell>
                  <TableCell>Suggested Comment</TableCell>
                  <TableCell>Created By</TableCell>
                  <TableCell>Approved By</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {approvedComments
                  .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
                  .map((comment) => {
                    const isItemSelected = isSelected(comment.id);
                    return (
                      <TableRow
                        key={comment.id}
                        hover
                        onClick={() => handleSelect(comment.id)}
                        role="checkbox"
                        aria-checked={isItemSelected}
                        selected={isItemSelected}
                      >
                        <TableCell padding="checkbox">
                          <Checkbox checked={isItemSelected} />
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
                        <TableCell sx={{ maxWidth: 200 }}>
                          <Typography variant="body2" noWrap>
                            {comment.current_comment || '-'}
                          </Typography>
                        </TableCell>
                        <TableCell sx={{ maxWidth: 250 }}>
                          <Typography variant="body2" noWrap>
                            {comment.suggested_comment}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2">{comment.created_by}</Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" color="success.main">
                            {comment.approved_by || '-'}
                          </Typography>
                          {comment.approved_at && (
                            <Typography variant="caption" display="block" color="text.secondary">
                              {new Date(comment.approved_at).toLocaleDateString()}
                            </Typography>
                          )}
                        </TableCell>
                        <TableCell>
                          <Button
                            size="small"
                            variant="contained"
                            color="primary"
                            startIcon={<ApplyIcon />}
                            onClick={(e) => {
                              e.stopPropagation();
                              handleApplyComment(comment);
                            }}
                            disabled={applying}
                          >
                            Apply
                          </Button>
                        </TableCell>
                      </TableRow>
                    );
                  })}
              </TableBody>
            </Table>
          </TableContainer>

          <TablePagination
            component="div"
            count={approvedComments.length}
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
      )}

      {/* Apply Confirmation Dialog */}
      <Dialog open={applyDialog} onClose={() => !applying && setApplyDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>Apply Comment to Databricks</DialogTitle>
        <DialogContent>
          {selectedComment && (
            <Box>
              <Alert severity="warning" sx={{ mb: 2 }}>
                This will update the metadata in Databricks. This action cannot be undone.
              </Alert>

              <Typography variant="subtitle2" gutterBottom>Entity:</Typography>
              <Typography variant="body2" fontFamily="monospace" mb={2}>
                {selectedComment.entity_path}
              </Typography>

              <Typography variant="subtitle2" gutterBottom>Current Comment:</Typography>
              <Typography variant="body2" mb={2}>
                {selectedComment.current_comment || '(none)'}
              </Typography>

              <Typography variant="subtitle2" gutterBottom>New Comment:</Typography>
              <Typography variant="body2" mb={2}>
                {selectedComment.suggested_comment}
              </Typography>

              {selectedComment.review_feedback && (
                <>
                  <Typography variant="subtitle2" gutterBottom>Reviewer Feedback:</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {selectedComment.review_feedback}
                  </Typography>
                </>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setApplyDialog(false)} disabled={applying}>
            Cancel
          </Button>
          <Button
            onClick={confirmApply}
            variant="contained"
            color="primary"
            disabled={applying}
            startIcon={applying ? <CircularProgress size={20} /> : <ApplyIcon />}
          >
            {applying ? 'Applying...' : 'Apply to Databricks'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ApplyQueue;