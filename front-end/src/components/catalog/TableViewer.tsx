import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  IconButton,
  Tooltip,
  TextField,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  Collapse,
  Card,
  CardContent,
  TablePagination,
} from '@mui/material';
import {
  Key as KeyIcon,
  FilterList as FilterIcon,
  Comment as CommentIcon,
  Edit as EditIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Info as InfoIcon,
  Storage as StorageIcon,
  Check as ApproveIcon,
  PlayArrow as ApplyIcon,
  RateReview as ReviewIcon,
  Schedule as PendingIcon,
} from '@mui/icons-material';
import { commentService } from '../../services/comment.service';

interface Column {
  name: string;
  data_type: string;
  comment: string | null;
  nullable: boolean;
  position: number;
  precision?: number | null;
  scale?: number | null;
  max_length?: number | null;
  default_value?: string | null;
  is_partition_key: boolean;
  is_primary_key: boolean;
}

interface TableMetadata {
  name: string;
  comment: string | null;
  table_type: string;
  columns_count: number;
  last_updated: string;
}

interface TableViewerProps {
  catalog: string;
  schema: string;
  table: string;
  tableMetadata: TableMetadata;
  columns: Column[];
  onCommentSuggestion?: (column: string, currentComment: string | null) => void;
  onApproveComment?: (column: string) => void;
  onApplyComment?: (column: string) => void;
  onTableCommentSuggestion?: (currentComment: string | null) => void;
  userRole?: string;
}

const TableViewer: React.FC<TableViewerProps> = ({
  catalog,
  schema,
  table,
  tableMetadata,
  columns,
  onCommentSuggestion,
  onApproveComment,
  onApplyComment,
  onTableCommentSuggestion,
  userRole = 'suggest_only'
}) => {
  console.log('TableViewer rendered with userRole:', userRole);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [filter, setFilter] = useState('');
  const [commentDialogOpen, setCommentDialogOpen] = useState(false);
  const [selectedColumn, setSelectedColumn] = useState<Column | null>(null);
  const [commentSuggestion, setCommentSuggestion] = useState('');
  const [expandedDetails, setExpandedDetails] = useState(false);
  const [pendingComments, setPendingComments] = useState<any[]>([]);
  const [loadingComments, setLoadingComments] = useState(false);
  const [reviewDialog, setReviewDialog] = useState(false);
  const [reviewingComment, setReviewingComment] = useState<any>(null);
  const [reviewFeedback, setReviewFeedback] = useState('');

  // Fetch pending comments for this table
  useEffect(() => {
    const fetchPendingComments = async () => {
      try {
        setLoadingComments(true);
        const comments = await commentService.getTableComments(catalog, schema, table);
        console.log('Fetched pending comments:', comments);
        console.log('Number of comments:', comments.length);
        setPendingComments(comments);
      } catch (error) {
        console.error('Failed to fetch pending comments:', error);
      } finally {
        setLoadingComments(false);
      }
    };

    fetchPendingComments();
  }, [catalog, schema, table]);

  const filteredColumns = columns.filter(col =>
    col.name.toLowerCase().includes(filter.toLowerCase()) ||
    (col.comment && col.comment.toLowerCase().includes(filter.toLowerCase())) ||
    col.data_type.toLowerCase().includes(filter.toLowerCase())
  );

  const paginatedColumns = filteredColumns.slice(
    page * rowsPerPage,
    page * rowsPerPage + rowsPerPage
  );

  // Get pending comments for a specific column
  const getColumnPendingComments = (columnName: string) => {
    const comments = pendingComments.filter(comment =>
      comment.entity_type === 'column' &&
      comment.entity_column === columnName
    );
    console.log(`getColumnPendingComments(${columnName}):`, comments);
    return comments;
  };

  // Get pending comments for table
  const getTablePendingComments = () => {
    return pendingComments.filter(comment => 
      comment.entity_type === 'table'
    );
  };

  const handleCommentClick = (column: Column) => {
    setSelectedColumn(column);
    setCommentSuggestion(column.comment || '');
    setCommentDialogOpen(true);
  };

  const handleCommentSubmit = async () => {
    if (!selectedColumn || !commentSuggestion.trim()) return;

    try {
      // Determine if this is a table or column comment based on data type
      const isTableComment = selectedColumn.data_type === 'TABLE';
      
      // Create the comment suggestion
      await commentService.createComment({
        entity_type: isTableComment ? 'table' : 'column',
        entity_catalog: catalog,
        entity_schema: schema,
        entity_table: table,
        entity_column: isTableComment ? undefined : selectedColumn.name,
        current_comment: selectedColumn.comment,
        suggested_comment: commentSuggestion,
      });

      // Refresh pending comments to show the new suggestion
      const updatedComments = await commentService.getTableComments(catalog, schema, table);
      setPendingComments(updatedComments);

      // Close dialog and reset state
      setCommentDialogOpen(false);
      setSelectedColumn(null);
      setCommentSuggestion('');
    } catch (error) {
      console.error('Failed to submit comment suggestion:', error);
    }
  };

  const handleApproveComment = (column: Column) => {
    console.log('handleApproveComment called for column:', column.name);
    // Find reviewable comment for this column (draft or pending)
    const columnPendingComments = getColumnPendingComments(column.name);
    console.log('Pending comments for column:', columnPendingComments);
    const reviewableComment = columnPendingComments.find(c => c.status === 'pending' || c.status === 'draft');
    console.log('Found reviewable comment:', reviewableComment);

    if (reviewableComment) {
      console.log('Opening review dialog');
      setReviewingComment(reviewableComment);
      setReviewFeedback('');
      setReviewDialog(true);
    } else {
      console.error('No reviewable comment found for column:', column.name);
      console.log('All pending comments:', pendingComments);
    }
  };

  const handleApplyComment = async (column: Column) => {
    // Find approved comment for this column
    const approvedComment = getColumnPendingComments(column.name).find(c => c.status === 'approved');
    if (approvedComment) {
      try {
        await commentService.applyComment(approvedComment.id);

        // Refresh pending comments
        const updatedComments = await commentService.getTableComments(catalog, schema, table);
        setPendingComments(updatedComments);
      } catch (error) {
        console.error('Failed to apply comment:', error);
      }
    }
  };

  const handleTableApproveComment = (comment: any) => {
    setReviewingComment(comment);
    setReviewFeedback('');
    setReviewDialog(true);
  };

  const handleTableApplyComment = async (comment: any) => {
    try {
      await commentService.applyComment(comment.id);
      
      // Refresh pending comments
      const updatedComments = await commentService.getTableComments(catalog, schema, table);
      setPendingComments(updatedComments);
    } catch (error) {
      console.error('Failed to apply table comment:', error);
    }
  };

  const handleApproveReview = async () => {
    if (!reviewingComment) return;

    try {
      await commentService.approveComment(reviewingComment.id, reviewFeedback || undefined);
      
      // Refresh pending comments
      const updatedComments = await commentService.getTableComments(catalog, schema, table);
      setPendingComments(updatedComments);
      
      // Close dialog
      setReviewDialog(false);
      setReviewingComment(null);
      setReviewFeedback('');
    } catch (error) {
      console.error('Failed to approve comment:', error);
    }
  };

  const handleRejectReview = async () => {
    if (!reviewingComment || !reviewFeedback.trim()) return;

    try {
      await commentService.rejectComment(reviewingComment.id, reviewFeedback);
      
      // Refresh pending comments
      const updatedComments = await commentService.getTableComments(catalog, schema, table);
      setPendingComments(updatedComments);
      
      // Close dialog
      setReviewDialog(false);
      setReviewingComment(null);
      setReviewFeedback('');
    } catch (error) {
      console.error('Failed to reject comment:', error);
    }
  };

  const handleTableCommentClick = () => {
    // Set up for table comment suggestion
    setSelectedColumn({
      name: table,
      data_type: 'TABLE',
      comment: tableMetadata.comment,
      nullable: false,
      position: 0,
      is_partition_key: false,
      is_primary_key: false
    } as Column);
    setCommentSuggestion(tableMetadata.comment || '');
    setCommentDialogOpen(true);
  };

  const getDataTypeDisplay = (column: Column) => {
    let typeStr = column.data_type;
    
    if (column.precision && column.scale) {
      typeStr += `(${column.precision},${column.scale})`;
    } else if (column.max_length) {
      typeStr += `(${column.max_length})`;
    }
    
    return typeStr;
  };

  const getDataTypeColor = (dataType: string) => {
    switch (dataType.toUpperCase()) {
      case 'STRING':
      case 'VARCHAR':
        return 'primary';
      case 'BIGINT':
      case 'INT':
      case 'INTEGER':
        return 'success';
      case 'DECIMAL':
      case 'DOUBLE':
      case 'FLOAT':
        return 'warning';
      case 'BOOLEAN':
        return 'secondary';
      case 'DATE':
      case 'TIMESTAMP':
        return 'info';
      default:
        return 'default';
    }
  };

  return (
    <Box data-testid="table-viewer">
      {/* Table Header Information */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box display="flex" alignItems="center" gap={2} mb={2}>
            <StorageIcon color="primary" />
            <Typography variant="h5" component="h1">
              {catalog}.{schema}.{table}
            </Typography>
          </Box>
          
          <Box display="flex" alignItems="center" gap={2} mb={2}>
            <Chip 
              label={tableMetadata.table_type} 
              size="small" 
              color="primary" 
              variant="outlined" 
            />
            <Typography variant="body2" color="text.secondary">
              {tableMetadata.columns_count} columns
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Last updated: {new Date(tableMetadata.last_updated).toLocaleDateString()}
            </Typography>
          </Box>

          <Box>
            <Box display="flex" alignItems="center" justifyContent="space-between" mb={1}>
              <Typography variant="body2" color="text.secondary">
                Description:
              </Typography>
              {(userRole === 'suggest_only' || userRole === 'approver' || userRole === 'admin') && (
                <Tooltip title="Suggest Table Comment">
                  <IconButton 
                    size="small" 
                    onClick={handleTableCommentClick}
                    color="primary"
                    data-testid="table-comment-edit"
                  >
                    <EditIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              )}
            </Box>
            <Typography variant="body1" sx={{ mb: 1 }}>
              {tableMetadata.comment || 'No description available'}
            </Typography>
            
            {/* Pending Table Comments */}
            {getTablePendingComments().map((pendingComment) => (
              <Box key={pendingComment.id} sx={{ mt: 1, p: 1, bgcolor: 'warning.light', borderRadius: 1 }} data-testid="pending-table-comment">
                <Box display="flex" alignItems="center" justifyContent="space-between" mb={0.5}>
                  <Box display="flex" alignItems="center" gap={0.5}>
                    <PendingIcon fontSize="small" color="warning" data-testid="pending-icon" />
                    <Chip 
                      label={pendingComment.status.toUpperCase()} 
                      size="small" 
                      color={pendingComment.status === 'pending' ? 'warning' : pendingComment.status === 'approved' ? 'success' : 'default'}
                      variant="outlined"
                    />
                    <Typography variant="caption" color="text.secondary">
                      Pending table description suggestion
                    </Typography>
                  </Box>
                  
                  {/* Table-level Action Buttons */}
                  <Box display="flex" alignItems="center" gap={1}>
                    {(userRole === 'approver' || userRole === 'admin') && pendingComment.status === 'pending' && (
                      <Tooltip title="Review Table Comment">
                        <IconButton 
                          size="small" 
                          onClick={() => handleTableApproveComment(pendingComment)}
                          color="primary"
                          data-testid="review-table-comment-button"
                        >
                          <ReviewIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    )}
                    {userRole === 'admin' && pendingComment.status === 'approved' && (
                      <Tooltip title="Apply Table Comment">
                        <IconButton 
                          size="small" 
                          onClick={() => handleTableApplyComment(pendingComment)}
                          color="success"
                          data-testid="apply-table-comment-button"
                        >
                          <ApplyIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    )}
                  </Box>
                </Box>
                <Typography variant="body2" sx={{ mb: 0.5 }}>
                  {pendingComment.suggested_comment}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  by {pendingComment.created_by} • {new Date(pendingComment.created_at).toLocaleDateString()}
                </Typography>
              </Box>
            ))}
          </Box>

          {/* Table Details Toggle */}
          <Box mt={2}>
            <Button
              startIcon={expandedDetails ? <ExpandLessIcon /> : <ExpandMoreIcon />}
              onClick={() => setExpandedDetails(!expandedDetails)}
              size="small"
            >
              {expandedDetails ? 'Hide' : 'Show'} Table Details
            </Button>
            
            <Collapse in={expandedDetails}>
              <Box mt={2} p={2} bgcolor="grey.50" borderRadius={1}>
                <Typography variant="body2" gutterBottom>
                  <strong>Full Path:</strong> {catalog}.{schema}.{table}
                </Typography>
                <Typography variant="body2" gutterBottom>
                  <strong>Type:</strong> {tableMetadata.table_type}
                </Typography>
                <Typography variant="body2" gutterBottom>
                  <strong>Columns:</strong> {tableMetadata.columns_count}
                </Typography>
                <Typography variant="body2">
                  <strong>Last Modified:</strong> {new Date(tableMetadata.last_updated).toLocaleString()}
                </Typography>
              </Box>
            </Collapse>
          </Box>
        </CardContent>
      </Card>

      {/* Columns Section */}
      <Paper>
        {/* Filter and Actions Bar */}
        <Box p={2} borderBottom={1} borderColor="divider">
          <Box display="flex" alignItems="center" justifyContent="space-between">
            <Typography variant="h6">
              Columns ({filteredColumns.length})
            </Typography>
            <Box display="flex" alignItems="center" gap={2}>
              <TextField
                size="small"
                placeholder="Filter columns..."
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                InputProps={{
                  startAdornment: <FilterIcon sx={{ mr: 1, color: 'text.secondary' }} />
                }}
              />
            </Box>
          </Box>
        </Box>

        {/* Columns Table */}
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>Nullable</TableCell>
                <TableCell>Default</TableCell>
                <TableCell>Keys</TableCell>
                <TableCell>Comment</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {paginatedColumns.map((column) => (
                <TableRow key={column.name} hover data-testid={`column-row-${column.name}`}>
                  <TableCell>
                    <Box display="flex" alignItems="center" gap={1}>
                      <Typography variant="body2" fontWeight="medium">
                        {column.name}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        #{column.position}
                      </Typography>
                    </Box>
                  </TableCell>
                  
                  <TableCell>
                    <Chip
                      label={getDataTypeDisplay(column)}
                      size="small"
                      color={getDataTypeColor(column.data_type) as any}
                      variant="outlined"
                    />
                  </TableCell>
                  
                  <TableCell>
                    <Chip
                      label={column.nullable ? 'Yes' : 'No'}
                      size="small"
                      color={column.nullable ? 'default' : 'error'}
                      variant="outlined"
                    />
                  </TableCell>
                  
                  <TableCell>
                    {column.default_value ? (
                      <Typography variant="body2" fontFamily="monospace">
                        {column.default_value}
                      </Typography>
                    ) : (
                      <Typography variant="body2" color="text.secondary">
                        NULL
                      </Typography>
                    )}
                  </TableCell>
                  
                  <TableCell>
                    <Box display="flex" gap={0.5}>
                      {column.is_primary_key && (
                        <Tooltip title="Primary Key">
                          <Chip
                            icon={<KeyIcon />}
                            label="PK"
                            size="small"
                            color="warning"
                            variant="filled"
                          />
                        </Tooltip>
                      )}
                      {column.is_partition_key && (
                        <Tooltip title="Partition Key">
                          <Chip
                            label="PART"
                            size="small"
                            color="info"
                            variant="outlined"
                          />
                        </Tooltip>
                      )}
                    </Box>
                  </TableCell>
                  
                  <TableCell sx={{ maxWidth: 300 }}>
                    <Box>
                      {/* Current Comment */}
                      {column.comment ? (
                        <Typography variant="body2" noWrap sx={{ mb: 0.5 }}>
                          {column.comment}
                        </Typography>
                      ) : (
                        <Typography variant="body2" color="text.secondary" fontStyle="italic" sx={{ mb: 0.5 }}>
                          No comment
                        </Typography>
                      )}
                      
                      {/* Pending Comments */}
                      {getColumnPendingComments(column.name).map((pendingComment) => (
                        <Box key={pendingComment.id} sx={{ mt: 0.5 }} data-testid="pending-comment">
                          <Box display="flex" alignItems="center" gap={0.5}>
                            <PendingIcon fontSize="small" color="warning" data-testid="pending-icon" />
                            <Chip 
                              label={pendingComment.status.toUpperCase()} 
                              size="small" 
                              color={pendingComment.status === 'pending' ? 'warning' : 'default'}
                              variant="outlined"
                            />
                          </Box>
                          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
                            Suggested: {pendingComment.suggested_comment}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            by {pendingComment.created_by} • {new Date(pendingComment.created_at).toLocaleDateString()}
                          </Typography>
                        </Box>
                      ))}
                    </Box>
                  </TableCell>
                  
                  <TableCell>
                    <Box display="flex" gap={0.5}>
                      <Tooltip title="View Details">
                        <IconButton size="small">
                          <InfoIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>

                      {/* Suggest Comment - Available to all roles */}
                      {(userRole === 'suggest_only' || userRole === 'approver' || userRole === 'admin') && (
                        <Tooltip title="Suggest Comment">
                          <IconButton
                            size="small"
                            onClick={() => handleCommentClick(column)}
                            color="primary"
                            data-testid="suggest-comment-button"
                          >
                            <CommentIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      )}

                      {/* Review/Approve Comment - Available to approvers and admins */}
                      {(() => {
                        const shouldShowReviewButton = userRole === 'approver' || userRole === 'admin';
                        // Check for both 'draft' and 'pending' status
                        const hasReviewableComments = getColumnPendingComments(column.name).some(c =>
                          c.status === 'pending' || c.status === 'draft'
                        );
                        console.log(`Review button for ${column.name}: role=${userRole}, shouldShow=${shouldShowReviewButton}, hasReviewable=${hasReviewableComments}`);

                        if (!shouldShowReviewButton) {
                          return null;
                        }

                        return (
                          <Tooltip title={hasReviewableComments ? "Review & Approve Comment" : "No pending comments"}>
                            <span style={{ display: 'inline-flex' }}>
                              <IconButton
                                size="small"
                                onClick={() => handleApproveComment(column)}
                                color="success"
                                data-testid="review-comment-button"
                                disabled={!hasReviewableComments}
                              >
                                <ReviewIcon fontSize="small" />
                              </IconButton>
                            </span>
                          </Tooltip>
                        );
                      })()}
                      
                      {/* Apply Comment - Available to admins */}
                      {userRole === 'admin' && (() => {
                        const hasApprovedComments = getColumnPendingComments(column.name).some(c => c.status === 'approved');
                        return (
                          <Tooltip title={hasApprovedComments ? "Apply Comment to Databricks" : "No approved comments"}>
                            <span>
                              <IconButton
                                size="small"
                                onClick={() => handleApplyComment(column)}
                                color="warning"
                                data-testid="apply-comment-button"
                                disabled={!hasApprovedComments}
                              >
                                <ApplyIcon fontSize="small" />
                              </IconButton>
                            </span>
                          </Tooltip>
                        );
                      })()}
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>

        {/* Pagination */}
        <TablePagination
          component="div"
          count={filteredColumns.length}
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

      {/* Comment Suggestion Dialog */}
      <Dialog 
        open={commentDialogOpen} 
        onClose={() => setCommentDialogOpen(false)}
        maxWidth="md"
        fullWidth
        data-testid="comment-dialog"
      >
        <DialogTitle>
          Suggest Comment for Column: {selectedColumn?.name}
        </DialogTitle>
        <DialogContent>
          <Box mb={2}>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              Column Type: {selectedColumn && getDataTypeDisplay(selectedColumn)}
            </Typography>
            {selectedColumn?.comment && (
              <Alert severity="info" sx={{ mb: 2 }}>
                <strong>Current comment:</strong> {selectedColumn.comment}
              </Alert>
            )}
          </Box>
          
          <TextField
            fullWidth
            multiline
            rows={4}
            label="Your comment suggestion"
            value={commentSuggestion}
            onChange={(e) => setCommentSuggestion(e.target.value)}
            placeholder="Describe what this column represents, its business meaning, or usage guidelines..."
            helperText="Provide a clear, business-focused description that will help other users understand this column"
            data-testid="comment-suggestion-input"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCommentDialogOpen(false)}>
            Cancel
          </Button>
          <Button 
            onClick={handleCommentSubmit}
            variant="contained"
            disabled={!commentSuggestion.trim()}
            data-testid="submit-suggestion-button"
          >
            Submit Suggestion
          </Button>
        </DialogActions>
      </Dialog>

      {/* Review/Approval Dialog */}
      <Dialog 
        open={reviewDialog} 
        onClose={() => setReviewDialog(false)}
        maxWidth="md"
        fullWidth
        data-testid="review-dialog"
      >
        <DialogTitle>
          Review Comment Suggestion
        </DialogTitle>
        <DialogContent>
          {reviewingComment && (
            <>
              <Alert severity="info" sx={{ mb: 2 }}>
                <Typography variant="subtitle2">Comment Details:</Typography>
                <Typography variant="body2">
                  <strong>Entity:</strong> {reviewingComment.entity_type === 'column' 
                    ? `${catalog}.${schema}.${table}.${reviewingComment.entity_column}`
                    : `${catalog}.${schema}.${table}`}
                </Typography>
                <Typography variant="body2">
                  <strong>Suggested by:</strong> {reviewingComment.created_by}
                </Typography>
                <Typography variant="body2">
                  <strong>Created:</strong> {new Date(reviewingComment.created_at).toLocaleString()}
                </Typography>
              </Alert>

              {reviewingComment.current_comment && (
                <Alert severity="info" sx={{ mb: 2 }}>
                  <Typography variant="subtitle2">Current Comment:</Typography>
                  <Typography variant="body2">{reviewingComment.current_comment}</Typography>
                </Alert>
              )}

              <Alert severity="warning" sx={{ mb: 2 }}>
                <Typography variant="subtitle2">Suggested Comment:</Typography>
                <Typography variant="body2">{reviewingComment.suggested_comment}</Typography>
              </Alert>

              <TextField
                fullWidth
                multiline
                rows={3}
                label="Review Feedback (Optional for approval, Required for rejection)"
                value={reviewFeedback}
                onChange={(e) => setReviewFeedback(e.target.value)}
                placeholder="Provide feedback about this suggestion..."
                helperText="Add any comments or feedback about this suggestion"
                data-testid="review-feedback-input"
              />
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setReviewDialog(false)}>Cancel</Button>
          <Button 
            onClick={handleRejectReview}
            color="error"
            disabled={!reviewFeedback.trim()}
            data-testid="reject-comment-button"
          >
            Reject
          </Button>
          <Button 
            onClick={handleApproveReview}
            variant="contained"
            color="success"
            data-testid="approve-comment-button"
          >
            Approve
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default TableViewer;