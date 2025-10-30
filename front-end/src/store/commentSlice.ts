import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit'
import { commentService } from '../services/comment.service'

export type CommentStatus = 'draft' | 'pending' | 'approved' | 'rejected' | 'applied'
export type EntityType = 'catalog' | 'schema' | 'table' | 'column'

export interface Comment {
  id: string
  entity_type: EntityType
  entity_catalog: string
  entity_schema: string | null
  entity_table: string | null
  entity_column: string | null
  current_comment: string | null
  suggested_comment: string
  status: CommentStatus
  created_by: string
  approved_by: string | null
  created_at: string
  updated_at: string
  submitted_at: string | null
  approved_at: string | null
  applied_at: string | null
  entity_path: string
  creator?: {
    username: string
    full_name: string
  }
  approver?: {
    username: string
    full_name: string
  }
}

export interface CommentCreate {
  entity_type: EntityType
  entity_catalog: string
  entity_schema?: string
  entity_table?: string
  entity_column?: string
  current_comment?: string
  suggested_comment: string
}

interface CommentState {
  comments: Comment[]
  myComments: Comment[]
  pendingApprovals: Comment[]
  selectedComment: Comment | null
  loading: boolean
  error: string | null
}

const initialState: CommentState = {
  comments: [],
  myComments: [],
  pendingApprovals: [],
  selectedComment: null,
  loading: false,
  error: null,
}

export const fetchComments = createAsyncThunk(
  'comments/fetchComments',
  async (filters?: { status?: CommentStatus; entity_catalog?: string }) => {
    const response = await commentService.listComments(filters)
    return response
  }
)

export const fetchMyComments = createAsyncThunk(
  'comments/fetchMyComments',
  async (status?: CommentStatus) => {
    const response = await commentService.listMyComments(status)
    return response
  }
)

export const fetchPendingApprovals = createAsyncThunk(
  'comments/fetchPendingApprovals',
  async () => {
    const response = await commentService.listPendingApprovals()
    return response
  }
)

export const createComment = createAsyncThunk(
  'comments/createComment',
  async (commentData: CommentCreate) => {
    const response = await commentService.createComment(commentData)
    return response
  }
)

export const updateComment = createAsyncThunk(
  'comments/updateComment',
  async ({ id, suggested_comment }: { id: string; suggested_comment: string }) => {
    const response = await commentService.updateComment(id, { suggested_comment })
    return response
  }
)

export const submitComments = createAsyncThunk(
  'comments/submitComments',
  async (commentIds: string[]) => {
    const response = await commentService.submitComments(commentIds)
    return response
  }
)

export const approveComment = createAsyncThunk(
  'comments/approveComment',
  async ({ id, feedback }: { id: string; feedback?: string }) => {
    const response = await commentService.approveComment(id, feedback)
    return response
  }
)

export const rejectComment = createAsyncThunk(
  'comments/rejectComment',
  async ({ id, feedback }: { id: string; feedback: string }) => {
    const response = await commentService.rejectComment(id, feedback)
    return response
  }
)

const commentSlice = createSlice({
  name: 'comments',
  initialState,
  reducers: {
    selectComment: (state, action: PayloadAction<Comment>) => {
      state.selectedComment = action.payload
    },
    clearSelectedComment: (state) => {
      state.selectedComment = null
    },
    clearError: (state) => {
      state.error = null
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch comments
      .addCase(fetchComments.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchComments.fulfilled, (state, action) => {
        state.loading = false
        state.comments = action.payload
      })
      .addCase(fetchComments.rejected, (state, action) => {
        state.loading = false
        state.error = action.error.message || 'Failed to fetch comments'
      })
      // Fetch my comments
      .addCase(fetchMyComments.fulfilled, (state, action) => {
        state.myComments = action.payload
      })
      // Fetch pending approvals
      .addCase(fetchPendingApprovals.fulfilled, (state, action) => {
        state.pendingApprovals = action.payload
      })
      // Create comment
      .addCase(createComment.fulfilled, (state, action) => {
        state.myComments.push(action.payload)
      })
      // Update comment
      .addCase(updateComment.fulfilled, (state, action) => {
        const index = state.myComments.findIndex(c => c.id === action.payload.id)
        if (index !== -1) {
          state.myComments[index] = action.payload
        }
      })
      // Approve comment
      .addCase(approveComment.fulfilled, (state, action) => {
        state.pendingApprovals = state.pendingApprovals.filter(
          c => c.id !== action.meta.arg.id
        )
      })
      // Reject comment
      .addCase(rejectComment.fulfilled, (state, action) => {
        state.pendingApprovals = state.pendingApprovals.filter(
          c => c.id !== action.meta.arg.id
        )
      })
  },
})

export const { selectComment, clearSelectedComment, clearError } = commentSlice.actions
export default commentSlice.reducer