import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useCommentsStore } from '../store/comments'
import { mockComments } from '../utils/mockData'

describe('Comments Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('initializes with empty state', () => {
    const store = useCommentsStore()
    
    expect(store.comments).toEqual([])
    expect(store.loading).toBe(false)
    expect(store.error).toBe(null)
    expect(store.hasMore).toBe(true)
  })

  it('calculates total comments correctly', () => {
    const store = useCommentsStore()
    store.comments = mockComments
    
    expect(store.totalComments).toBe(mockComments.length)
  })

  it('finds comment by ID', () => {
    const store = useCommentsStore()
    store.comments = mockComments
    
    const comment = store.getCommentById(1)
    expect(comment).toEqual(mockComments[0])
    
    const nonExistent = store.getCommentById(999)
    expect(nonExistent).toBeUndefined()
  })

  it('clears comments and resets state', () => {
    const store = useCommentsStore()
    store.comments = mockComments
    store.error = 'Some error'
    
    store.clearComments()
    
    expect(store.comments).toEqual([])
    expect(store.error).toBe(null)
    expect(store.pagination.currentPage).toBe(1)
    expect(store.hasMore).toBe(true)
  })

  it('clears error', () => {
    const store = useCommentsStore()
    store.error = 'Some error'
    
    store.clearError()
    
    expect(store.error).toBe(null)
  })
})
