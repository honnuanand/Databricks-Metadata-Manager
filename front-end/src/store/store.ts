import { configureStore } from '@reduxjs/toolkit'
import authReducer from './authSlice'
import catalogReducer from './catalogSlice'
import commentReducer from './commentSlice'

export const store = configureStore({
  reducer: {
    auth: authReducer,
    catalog: catalogReducer,
    comments: commentReducer,
  },
})

export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch