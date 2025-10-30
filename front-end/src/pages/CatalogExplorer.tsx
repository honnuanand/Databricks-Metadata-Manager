import React, { useEffect, useState } from 'react'
import {
  Box,
  Typography,
  Grid,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  TextField,
  InputAdornment,
  Chip,
  Badge,
  CircularProgress,
  Alert,
  Paper,
  Divider,
  IconButton,
  Tooltip,
} from '@mui/material'
import {
  Storage as DatabaseIcon,
  Folder as SchemaIcon,
  TableChart as TableIcon,
  Search as SearchIcon,
  ExpandMore as ExpandMoreIcon,
  Warning as WarningIcon,
  CheckCircle as ApprovedIcon,
  Schedule as PendingIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material'
import { useDispatch, useSelector } from 'react-redux'
import { RootState, AppDispatch } from '../store/store'
import { 
  fetchCatalogs, 
  fetchSchemas, 
  fetchTables, 
  fetchColumns,
  selectCatalog, 
  selectSchema, 
  selectTable,
  clearError
} from '../store/catalogSlice'
import { commentService } from '../services/comment.service'
import TableViewer from '../components/catalog/TableViewer'

interface PendingCommentSummary {
  [key: string]: {
    pending: number
    approved: number
    needsChanges: number
  }
}

export default function CatalogExplorer() {
  const dispatch = useDispatch<AppDispatch>()
  const {
    catalogs,
    schemas,
    tables,
    columns,
    selectedCatalog,
    selectedSchema,
    selectedTable,
    loading,
    error,
  } = useSelector((state: RootState) => state.catalog)
  
  const { user } = useSelector((state: RootState) => state.auth)

  console.log('CatalogExplorer - Current user:', user);
  console.log('CatalogExplorer - User role:', user?.role);

  const [search, setSearch] = useState('')
  const [expandedCatalogs, setExpandedCatalogs] = useState<Set<string>>(new Set())
  const [expandedSchemas, setExpandedSchemas] = useState<Set<string>>(new Set())
  const [pendingComments, setPendingComments] = useState<PendingCommentSummary>({})
  const [selectedTableMetadata, setSelectedTableMetadata] = useState<any>(null)

  useEffect(() => {
    dispatch(fetchCatalogs())
    loadPendingComments()
  }, [dispatch])

  // Debug logging
  useEffect(() => {
    console.log('CatalogExplorer Debug:', {
      catalogs: catalogs.length,
      schemas: schemas.length,
      tables: tables.length,
      selectedCatalog,
      selectedSchema,
      expandedCatalogs: Array.from(expandedCatalogs),
      expandedSchemas: Array.from(expandedSchemas),
      loading
    })
  }, [catalogs, schemas, tables, selectedCatalog, selectedSchema, expandedCatalogs, expandedSchemas, loading])

  const loadPendingComments = async () => {
    try {
      const comments = await commentService.listComments({ status: 'pending' })
      const approved = await commentService.listComments({ status: 'approved' })
      const changesRequested = await commentService.listComments({ status: 'changes_requested' })
      
      const summary: PendingCommentSummary = {}
      
      // Process all comment types
      const allComments = [
        ...comments.map(c => ({ ...c, type: 'pending' })),
        ...approved.map(c => ({ ...c, type: 'approved' })),
        ...changesRequested.map(c => ({ ...c, type: 'changes_requested' }))
      ]
      
      allComments.forEach(comment => {
        const catalogKey = comment.entity_catalog
        const schemaKey = `${comment.entity_catalog}.${comment.entity_schema}`
        const tableKey = `${comment.entity_catalog}.${comment.entity_schema}.${comment.entity_table}`
        
        // Initialize if doesn't exist
        if (!summary[catalogKey]) summary[catalogKey] = { pending: 0, approved: 0, needsChanges: 0 }
        if (!summary[schemaKey]) summary[schemaKey] = { pending: 0, approved: 0, needsChanges: 0 }
        if (!summary[tableKey]) summary[tableKey] = { pending: 0, approved: 0, needsChanges: 0 }
        
        // Increment counts
        if (comment.type === 'pending') {
          summary[catalogKey].pending++
          summary[schemaKey].pending++
          summary[tableKey].pending++
        } else if (comment.type === 'approved') {
          summary[catalogKey].approved++
          summary[schemaKey].approved++
          summary[tableKey].approved++
        } else if (comment.type === 'changes_requested') {
          summary[catalogKey].needsChanges++
          summary[schemaKey].needsChanges++
          summary[tableKey].needsChanges++
        }
      })
      
      setPendingComments(summary)
    } catch (error) {
      console.error('Failed to load pending comments:', error)
    }
  }

  const handleCatalogToggle = async (catalogName: string) => {
    const newExpanded = new Set(expandedCatalogs)
    if (expandedCatalogs.has(catalogName)) {
      newExpanded.delete(catalogName)
    } else {
      newExpanded.add(catalogName)
      // Load schemas for this catalog
      dispatch(selectCatalog(catalogName))
      dispatch(fetchSchemas({ catalog: catalogName }))
    }
    setExpandedCatalogs(newExpanded)
  }

  const handleSchemaToggle = async (catalogName: string, schemaName: string) => {
    const schemaKey = `${catalogName}.${schemaName}`
    const newExpanded = new Set(expandedSchemas)
    if (expandedSchemas.has(schemaKey)) {
      newExpanded.delete(schemaKey)
    } else {
      newExpanded.add(schemaKey)
      // Load tables for this schema
      dispatch(selectSchema(schemaName))
      dispatch(fetchTables({ catalog: catalogName, schema: schemaName }))
    }
    setExpandedSchemas(newExpanded)
  }

  const handleTableSelect = async (catalogName: string, schemaName: string, tableName: string) => {
    dispatch(selectTable(tableName))
    
    // Find table metadata
    const table = tables.find(t => t.name === tableName)
    if (table) {
      setSelectedTableMetadata({
        name: tableName,
        comment: table.comment,
        table_type: table.table_type || 'TABLE',
        columns_count: table.column_count || 0,
        last_updated: table.updated_at || new Date().toISOString(),
      })
      
      // Load columns
      dispatch(fetchColumns({ catalog: catalogName, schema: schemaName, table: tableName }))
    }
  }

  const getStatusBadge = (key: string) => {
    const stats = pendingComments[key]
    if (!stats || (stats.pending === 0 && stats.approved === 0 && stats.needsChanges === 0)) {
      return null
    }

    return (
      <Box display="flex" gap={0.5} alignItems="center">
        {stats.pending > 0 && (
          <Badge badgeContent={stats.pending} color="warning">
            <PendingIcon fontSize="small" color="warning" />
          </Badge>
        )}
        {stats.approved > 0 && (user?.role === 'admin' || user?.role === 'approver') && (
          <Badge badgeContent={stats.approved} color="success">
            <ApprovedIcon fontSize="small" color="success" />
          </Badge>
        )}
        {stats.needsChanges > 0 && (
          <Badge badgeContent={stats.needsChanges} color="error">
            <WarningIcon fontSize="small" color="error" />
          </Badge>
        )}
      </Box>
    )
  }

  const filteredCatalogs = catalogs.filter(catalog =>
    catalog.name.toLowerCase().includes(search.toLowerCase())
  )

  const filteredSchemas = schemas.filter(schema =>
    !search || schema.name.toLowerCase().includes(search.toLowerCase())
  )

  const filteredTables = tables.filter(table =>
    !search || table.name.toLowerCase().includes(search.toLowerCase())
  )

  if (loading && catalogs.length === 0) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    )
  }

  if (error) {
    return (
      <Box p={3}>
        <Alert severity="error" onClose={() => dispatch(clearError())}>
          {error}
        </Alert>
      </Box>
    )
  }

  // If a table is selected, show the TableViewer
  if (selectedTable && selectedTableMetadata && selectedCatalog && selectedSchema) {
    return (
      <Box p={3}>
        <Box mb={2}>
          <Typography 
            variant="body2" 
            color="primary" 
            sx={{ cursor: 'pointer' }}
            onClick={() => {
              dispatch(selectTable(''))
              setSelectedTableMetadata(null)
            }}
          >
            ← Back to Catalog Explorer
          </Typography>
        </Box>
        <TableViewer
          catalog={selectedCatalog}
          schema={selectedSchema}
          table={selectedTable}
          tableMetadata={selectedTableMetadata}
          columns={columns.map(col => ({
            name: col.name,
            data_type: col.data_type,
            comment: col.comment,
            nullable: col.nullable,
            position: col.position || 0,
            is_partition_key: col.partition_index !== null,
            is_primary_key: false, // This would need to come from the API
          }))}
          userRole={user?.role}
        />
      </Box>
    )
  }

  const handleRefresh = () => {
    dispatch(fetchCatalogs())
    loadPendingComments()
  }

  return (
    <Box p={3}>
      {/* Header */}
      <Box mb={3} display="flex" justifyContent="space-between" alignItems="flex-start">
        <Box>
          <Typography variant="h4" component="h1" gutterBottom>
            Catalog Explorer
          </Typography>
          <Typography variant="body1" color="text.secondary" gutterBottom>
            Browse and explore your Databricks Unity Catalog metadata
          </Typography>
        </Box>
        <Tooltip title="Refresh catalog list">
          <IconButton
            onClick={handleRefresh}
            color="primary"
            disabled={loading}
          >
            <RefreshIcon />
          </IconButton>
        </Tooltip>
      </Box>

      <Grid container spacing={3}>
        {/* Left Panel - Tree View */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2, height: 'calc(100vh - 200px)', overflow: 'auto' }}>
            {/* Search */}
            <Box mb={2}>
              <TextField
                fullWidth
                size="small"
                placeholder="Search catalogs, schemas, tables..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchIcon />
                    </InputAdornment>
                  ),
                }}
              />
            </Box>

            {/* Catalog Tree */}
            <Box>
              {filteredCatalogs.map((catalog) => (
                <Accordion
                  key={catalog.name}
                  expanded={expandedCatalogs.has(catalog.name)}
                  onChange={() => handleCatalogToggle(catalog.name)}
                  sx={{ 
                    '&:before': { display: 'none' },
                    boxShadow: 'none',
                    border: '1px solid',
                    borderColor: 'divider',
                    mb: 1,
                  }}
                >
                  <AccordionSummary
                    expandIcon={<ExpandMoreIcon />}
                    sx={{ 
                      '& .MuiAccordionSummary-content': { 
                        alignItems: 'center',
                        gap: 1
                      }
                    }}
                  >
                    <DatabaseIcon color="primary" />
                    <Typography variant="body1" sx={{ flexGrow: 1 }}>
                      {catalog.name}
                    </Typography>
                    {getStatusBadge(catalog.name)}
                    <Chip
                      label={`${schemas.filter(s => s.catalog_name === catalog.name).length} schemas`}
                      size="small"
                      variant="outlined"
                    />
                  </AccordionSummary>
                  <AccordionDetails sx={{ pt: 0 }}>
                    {loading && (schemas.length === 0 || !schemas.some(s => s.catalog_name === catalog.name)) ? (
                      <Box display="flex" justifyContent="center" py={2}>
                        <CircularProgress size={20} />
                        <Typography variant="body2" sx={{ ml: 1 }}>
                          Loading schemas...
                        </Typography>
                      </Box>
                    ) : (
                      <List dense sx={{ pl: 2 }}>
                        {filteredSchemas
                          .filter(schema => schema.catalog_name === catalog.name)
                          .map((schema) => {
                            const schemaKey = `${catalog.name}.${schema.name}`
                            return (
                              <React.Fragment key={schema.name}>
                                <ListItem disablePadding>
                                  <ListItemButton
                                    onClick={() => handleSchemaToggle(catalog.name, schema.name)}
                                    sx={{ py: 0.5 }}
                                  >
                                    <ListItemIcon sx={{ minWidth: 32 }}>
                                      <ExpandMoreIcon 
                                        sx={{ 
                                          transform: expandedSchemas.has(schemaKey) ? 'rotate(0deg)' : 'rotate(-90deg)',
                                          transition: 'transform 0.2s'
                                        }} 
                                      />
                                    </ListItemIcon>
                                    <ListItemIcon sx={{ minWidth: 32 }}>
                                      <SchemaIcon color="action" fontSize="small" />
                                    </ListItemIcon>
                                    <ListItemText 
                                      primary={
                                        <Box display="flex" alignItems="center" justifyContent="space-between">
                                          <Typography variant="body2">{schema.name}</Typography>
                                          <Box display="flex" alignItems="center" gap={1}>
                                            {getStatusBadge(schemaKey)}
                                            <Chip
                                              label={`${tables.filter(t => t.catalog_name === catalog.name && t.schema_name === schema.name).length} tables`}
                                              size="small"
                                              variant="outlined"
                                            />
                                          </Box>
                                        </Box>
                                      }
                                    />
                                  </ListItemButton>
                                </ListItem>
                                
                                {/* Tables List */}
                                {expandedSchemas.has(schemaKey) && (
                                  <List dense sx={{ pl: 4, bgcolor: 'grey.50' }}>
                                    {loading && (tables.length === 0 || !tables.some(t => t.catalog_name === catalog.name && t.schema_name === schema.name)) ? (
                                      <ListItem>
                                        <CircularProgress size={16} />
                                        <Typography variant="body2" sx={{ ml: 1 }}>
                                          Loading tables...
                                        </Typography>
                                      </ListItem>
                                    ) : (
                                      filteredTables
                                        .filter(table => 
                                          table.catalog_name === catalog.name && 
                                          table.schema_name === schema.name
                                        )
                                        .map((table) => {
                                          const tableKey = `${catalog.name}.${schema.name}.${table.name}`
                                          return (
                                            <ListItem key={table.name} disablePadding>
                                              <ListItemButton
                                                onClick={() => handleTableSelect(catalog.name, schema.name, table.name)}
                                                sx={{ py: 0.25 }}
                                              >
                                                <ListItemIcon sx={{ minWidth: 32 }}>
                                                  <TableIcon color="action" fontSize="small" />
                                                </ListItemIcon>
                                                <ListItemText 
                                                  primary={
                                                    <Box display="flex" alignItems="center" justifyContent="space-between">
                                                      <Typography variant="body2">{table.name}</Typography>
                                                      <Box display="flex" alignItems="center" gap={1}>
                                                        {getStatusBadge(tableKey)}
                                                        <Chip 
                                                          label={table.table_type || 'TABLE'} 
                                                          size="small" 
                                                          color="primary"
                                                          variant="outlined" 
                                                        />
                                                      </Box>
                                                    </Box>
                                                  }
                                                />
                                              </ListItemButton>
                                            </ListItem>
                                          )
                                        })
                                    )}
                                  </List>
                                )}
                              </React.Fragment>
                            )
                          })}
                      </List>
                    )}
                  </AccordionDetails>
                </Accordion>
              ))}
            </Box>

            {/* No Results */}
            {filteredCatalogs.length === 0 && !loading && (
              <Box textAlign="center" py={4}>
                <Typography variant="h6" color="text.secondary">
                  No catalogs found
                </Typography>
                {search && (
                  <Typography variant="body2" color="text.secondary">
                    Try adjusting your search criteria
                  </Typography>
                )}
              </Box>
            )}
          </Paper>
        </Grid>

        {/* Right Panel - Instructions */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, height: 'calc(100vh - 200px)', overflow: 'auto' }}>
            <Typography variant="h6" gutterBottom>
              How to use the Catalog Explorer
            </Typography>
            <Typography variant="body2" paragraph>
              1. <strong>Browse Catalogs:</strong> Click on any catalog to expand and see its schemas
            </Typography>
            <Typography variant="body2" paragraph>
              2. <strong>Explore Schemas:</strong> Click on a schema to expand and see its tables
            </Typography>
            <Typography variant="body2" paragraph>
              3. <strong>View Tables:</strong> Click on any table to see its detailed schema, columns, and metadata
            </Typography>
            
            <Divider sx={{ my: 2 }} />
            
            <Typography variant="h6" gutterBottom>
              Comment Status Indicators
            </Typography>
            <Box display="flex" flexDirection="column" gap={1}>
              <Box display="flex" alignItems="center" gap={1}>
                <PendingIcon color="warning" fontSize="small" />
                <Typography variant="body2">
                  <strong>Pending:</strong> Comments awaiting approval
                </Typography>
              </Box>
              {(user?.role === 'admin' || user?.role === 'approver') && (
                <Box display="flex" alignItems="center" gap={1}>
                  <ApprovedIcon color="success" fontSize="small" />
                  <Typography variant="body2">
                    <strong>Approved:</strong> Comments ready to be applied
                  </Typography>
                </Box>
              )}
              <Box display="flex" alignItems="center" gap={1}>
                <WarningIcon color="error" fontSize="small" />
                <Typography variant="body2">
                  <strong>Changes Requested:</strong> Comments that need revision
                </Typography>
              </Box>
            </Box>

            <Divider sx={{ my: 2 }} />

            <Typography variant="h6" gutterBottom>
              User Role: {user?.role === 'suggest_only' ? 'Suggestion Only' : user?.role?.charAt(0).toUpperCase() + user?.role?.slice(1)}
            </Typography>
            <Typography variant="body2">
              {user?.role === 'suggest_only' && 'You can create comment suggestions and view their status.'}
              {user?.role === 'approver' && 'You can create suggestions, review and approve/reject comments, and apply approved comments.'}
              {user?.role === 'admin' && 'You have full access to create, review, approve, and apply all comments.'}
            </Typography>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  )
}