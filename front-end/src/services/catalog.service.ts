import api from './api'
import { Catalog, Schema, Table, Column } from '../store/catalogSlice'

class CatalogService {
  async listCatalogs(search?: string): Promise<Catalog[]> {
    const response = await api.get('/api/v1/catalogs/', {
      params: { search },
    })
    // Handle both old format (direct array) and new format (wrapped object)
    if (Array.isArray(response.data)) {
      return response.data
    }
    return response.data.catalogs || []
  }

  async listSchemas(catalog: string, search?: string): Promise<Schema[]> {
    const response = await api.get(`/api/v1/catalogs/${catalog}/schemas`, {
      params: { search },
    })
    // Handle both old format (direct array) and new format (wrapped object)
    if (Array.isArray(response.data)) {
      return response.data
    }
    return response.data.schemas || []
  }

  async listTables(catalog: string, schema: string, search?: string): Promise<Table[]> {
    const response = await api.get(`/api/v1/catalogs/${catalog}/${schema}/tables`, {
      params: { search },
    })
    // Handle both old format (direct array) and new format (wrapped object)
    if (Array.isArray(response.data)) {
      return response.data
    }
    return response.data.tables || []
  }

  async getTableColumns(catalog: string, schema: string, table: string): Promise<Column[]> {
    const response = await api.get(`/api/v1/catalogs/${catalog}/${schema}/${table}/columns`)
    // Handle both old format (direct array) and new format (wrapped object)
    if (Array.isArray(response.data)) {
      return response.data
    }
    return response.data.columns || []
  }
}

export const catalogService = new CatalogService()