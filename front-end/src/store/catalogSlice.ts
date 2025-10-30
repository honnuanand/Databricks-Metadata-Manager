import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit'
import { catalogService } from '../services/catalog.service'

export interface Catalog {
  name: string
  comment: string | null
  owner: string | null
  created_at: string | null
  updated_at: string | null
  table_count: number
  schema_count: number
}

export interface Schema {
  catalog_name: string
  name: string
  full_name: string
  comment: string | null
  owner: string | null
  created_at: string | null
  updated_at: string | null
  table_count: number
}

export interface Table {
  catalog_name: string
  schema_name: string
  name: string
  full_name: string
  table_type: string | null
  comment: string | null
  owner: string | null
  created_at: string | null
  updated_at: string | null
  column_count: number
  row_count: number | null
}

export interface Column {
  catalog_name: string
  schema_name: string
  table_name: string
  name: string
  full_name: string
  data_type: string
  comment: string | null
  nullable: boolean
  partition_index: number | null
  position: number | null
}

interface CatalogState {
  catalogs: Catalog[]
  schemas: Schema[]
  tables: Table[]
  columns: Column[]
  selectedCatalog: string | null
  selectedSchema: string | null
  selectedTable: string | null
  loading: boolean
  error: string | null
}

const initialState: CatalogState = {
  catalogs: [],
  schemas: [],
  tables: [],
  columns: [],
  selectedCatalog: null,
  selectedSchema: null,
  selectedTable: null,
  loading: false,
  error: null,
}

export const fetchCatalogs = createAsyncThunk(
  'catalog/fetchCatalogs',
  async (search?: string) => {
    const response = await catalogService.listCatalogs(search)
    return response
  }
)

export const fetchSchemas = createAsyncThunk(
  'catalog/fetchSchemas',
  async ({ catalog, search }: { catalog: string; search?: string }) => {
    const response = await catalogService.listSchemas(catalog, search)
    return response
  }
)

export const fetchTables = createAsyncThunk(
  'catalog/fetchTables',
  async ({ catalog, schema, search }: { catalog: string; schema: string; search?: string }) => {
    const response = await catalogService.listTables(catalog, schema, search)
    return response
  }
)

export const fetchColumns = createAsyncThunk(
  'catalog/fetchColumns',
  async ({ catalog, schema, table }: { catalog: string; schema: string; table: string }) => {
    const response = await catalogService.getTableColumns(catalog, schema, table)
    return response
  }
)

const catalogSlice = createSlice({
  name: 'catalog',
  initialState,
  reducers: {
    selectCatalog: (state, action: PayloadAction<string>) => {
      state.selectedCatalog = action.payload
      state.selectedSchema = null
      state.selectedTable = null
      state.schemas = []
      state.tables = []
      state.columns = []
    },
    selectSchema: (state, action: PayloadAction<string>) => {
      state.selectedSchema = action.payload
      state.selectedTable = null
      state.tables = []
      state.columns = []
    },
    selectTable: (state, action: PayloadAction<string>) => {
      state.selectedTable = action.payload
      state.columns = []
    },
    clearError: (state) => {
      state.error = null
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch catalogs
      .addCase(fetchCatalogs.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchCatalogs.fulfilled, (state, action) => {
        state.loading = false
        state.catalogs = action.payload
      })
      .addCase(fetchCatalogs.rejected, (state, action) => {
        state.loading = false
        state.error = action.error.message || 'Failed to fetch catalogs'
      })
      // Fetch schemas
      .addCase(fetchSchemas.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchSchemas.fulfilled, (state, action) => {
        state.loading = false
        state.schemas = action.payload
      })
      .addCase(fetchSchemas.rejected, (state, action) => {
        state.loading = false
        state.error = action.error.message || 'Failed to fetch schemas'
      })
      // Fetch tables
      .addCase(fetchTables.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchTables.fulfilled, (state, action) => {
        state.loading = false
        state.tables = action.payload
      })
      .addCase(fetchTables.rejected, (state, action) => {
        state.loading = false
        state.error = action.error.message || 'Failed to fetch tables'
      })
      // Fetch columns
      .addCase(fetchColumns.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchColumns.fulfilled, (state, action) => {
        state.loading = false
        state.columns = action.payload
      })
      .addCase(fetchColumns.rejected, (state, action) => {
        state.loading = false
        state.error = action.error.message || 'Failed to fetch columns'
      })
  },
})

export const { selectCatalog, selectSchema, selectTable, clearError } = catalogSlice.actions
export default catalogSlice.reducer