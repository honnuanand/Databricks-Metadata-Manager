// Catalog and schema tests for Metadata Manager
import { TestCategory } from '../types';
import { assert } from '../utils/assertions';
import api from '../../services/api';

export const catalogTests: TestCategory = {
  name: 'Catalogs & Schemas',
  description: 'Tests for browsing catalogs, schemas, and tables',
  tests: [
    {
      name: 'List Catalogs',
      description: 'Test fetching list of catalogs',
      fn: async () => {
        // First login to get token
        const loginResponse = await api.post('/api/v1/auth/login', {
          username: 'admin@example.com',
          password: 'admin123',
        });

        const token = loginResponse.data.access_token;

        // Get catalogs
        const response = await api.get('/api/v1/catalogs/', {
          headers: {
            'X-Auth-Token': token,
            Authorization: `Bearer ${token}`,
          },
        });

        assert.statusCode(response.status, 200, 'Should return 200');
        assert.hasProperty(response.data, 'catalogs', 'Should have catalogs array');
        assert.isArray(response.data.catalogs, 'Catalogs should be an array');
      },
    },
    {
      name: 'Get Catalog Details',
      description: 'Test fetching details of a specific catalog',
      fn: async () => {
        const loginResponse = await api.post('/api/v1/auth/login', {
          username: 'admin@example.com',
          password: 'admin123',
        });

        const token = loginResponse.data.access_token;

        // First get list of catalogs
        const catalogsResponse = await api.get('/api/v1/catalogs/', {
          headers: {
            'X-Auth-Token': token,
            Authorization: `Bearer ${token}`,
          },
        });

        if (catalogsResponse.data.catalogs.length === 0) {
          throw new Error('No catalogs available to test');
        }

        const catalogName = catalogsResponse.data.catalogs[0].name;

        // Get catalog details
        const response = await api.get(`/api/v1/catalogs/${catalogName}`, {
          headers: {
            'X-Auth-Token': token,
            Authorization: `Bearer ${token}`,
          },
        });

        assert.statusCode(response.status, 200, 'Should return 200');
        assert.hasProperty(response.data, 'catalog', 'Should have catalog object');
      },
    },
    {
      name: 'List Schemas in Catalog',
      description: 'Test fetching schemas for a catalog',
      fn: async () => {
        const loginResponse = await api.post('/api/v1/auth/login', {
          username: 'admin@example.com',
          password: 'admin123',
        });

        const token = loginResponse.data.access_token;

        // First get list of catalogs
        const catalogsResponse = await api.get('/api/v1/catalogs/', {
          headers: {
            'X-Auth-Token': token,
            Authorization: `Bearer ${token}`,
          },
        });

        if (catalogsResponse.data.catalogs.length === 0) {
          throw new Error('No catalogs available to test');
        }

        const catalogName = catalogsResponse.data.catalogs[0].name;

        // Get schemas
        const response = await api.get(`/api/v1/catalogs/${catalogName}/schemas`, {
          headers: {
            'X-Auth-Token': token,
            Authorization: `Bearer ${token}`,
          },
        });

        assert.statusCode(response.status, 200, 'Should return 200');
        assert.hasProperty(response.data, 'schemas', 'Should have schemas array');
        assert.isArray(response.data.schemas, 'Schemas should be an array');
      },
    },
    {
      name: 'Regular User Can Browse Catalogs',
      description: 'Test that regular users can browse catalogs',
      fn: async () => {
        const loginResponse = await api.post('/api/v1/auth/login', {
          username: 'user@example.com',
          password: 'user123',
        });

        const token = loginResponse.data.access_token;

        const response = await api.get('/api/v1/catalogs/', {
          headers: {
            'X-Auth-Token': token,
            Authorization: `Bearer ${token}`,
          },
        });

        assert.statusCode(response.status, 200, 'Regular user should be able to browse catalogs');
      },
    },
  ],
};
