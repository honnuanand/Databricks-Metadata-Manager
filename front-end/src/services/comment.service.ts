import api from './api'
import { Comment, CommentCreate, CommentStatus } from '../store/commentSlice'

interface CommentFilters {
  status?: CommentStatus
  entity_catalog?: string
  entity_schema?: string
  entity_table?: string
  created_by?: string
}

interface CommentUpdate {
  suggested_comment: string
}

class CommentService {
  async getAllComments(): Promise<Comment[]> {
    const response = await api.get('/api/v1/comments')
    return response.data
  }

  async listComments(filters?: CommentFilters): Promise<Comment[]> {
    const response = await api.get('/api/v1/comments', {
      params: filters,
    })
    return response.data
  }
  
  async listMyComments(status?: CommentStatus): Promise<Comment[]> {
    const response = await api.get('/api/v1/comments/my', {
      params: { status },
    })
    return response.data
  }
  
  async listPendingApprovals(): Promise<Comment[]> {
    const response = await api.get('/api/v1/approvals/pending')
    return response.data
  }
  
  async getTableComments(catalog: string, schema: string, table: string): Promise<Comment[]> {
    const response = await api.get(`/api/v1/comments/table/${catalog}/${schema}/${table}`)
    return response.data
  }
  
  async getComment(id: string): Promise<Comment> {
    const response = await api.get(`/api/v1/comments/${id}`)
    return response.data
  }
  
  async createComment(commentData: CommentCreate): Promise<Comment> {
    const response = await api.post('/api/v1/comments', commentData)
    return response.data
  }
  
  async updateComment(id: string, update: CommentUpdate): Promise<Comment> {
    const response = await api.put(`/api/v1/comments/${id}`, update)
    return response.data
  }
  
  async deleteComment(id: string): Promise<void> {
    await api.delete(`/api/v1/comments/${id}`)
  }
  
  async submitComments(commentIds: string[]): Promise<any> {
    const response = await api.post('/api/v1/comments/submit', {
      comment_ids: commentIds,
    })
    return response.data
  }
  
  async approveComment(id: string, feedback?: string): Promise<any> {
    const response = await api.post(`/api/v1/approvals/${id}/approve`, null, {
      params: { feedback },
    })
    return response.data
  }
  
  async rejectComment(id: string, feedback: string): Promise<any> {
    const response = await api.post(`/api/v1/approvals/${id}/reject`, null, {
      params: { feedback },
    })
    return response.data
  }
  
  async requestChanges(id: string, feedback: string): Promise<any> {
    const response = await api.post(`/api/v1/approvals/${id}/request-changes`, null, {
      params: { feedback },
    })
    return response.data
  }
  
  async applyComment(id: string): Promise<any> {
    const response = await api.post(`/api/v1/approvals/${id}/apply`)
    return response.data
  }
  
  async batchApprove(commentIds: string[], action: 'approved' | 'rejected', feedback?: string): Promise<any> {
    const response = await api.post('/api/v1/approvals/batch', {
      comment_ids: commentIds,
      action,
      feedback,
    })
    return response.data
  }
}

export const commentService = new CommentService()