import { defineStore } from 'pinia'
import api from '../services/api'

export const useCommentsStore = defineStore('comments', {
  state: () => ({
    comments: [],
    loading: false,
    error: null,
    pagination: {
      currentPage: 1,
      totalPages: 1,
      totalItems: 0,
      itemsPerPage: 10
    },
    hasMore: true
  }),
  
  getters: {
    getCommentById: (state) => (id) => {
      return state.comments.find(comment => comment.id === id)
    },
    
    totalComments: (state) => {
      return state.comments.length
    },
    
    isLoading: (state) => {
      return state.loading
    }
  },
  
  actions: {
    async fetchComments(page = 1, refresh = false) {
      this.loading = true
      this.error = null
      
      try {
        const response = await api.get('/comments/', {
          params: {
            page,
            page_size: this.pagination.itemsPerPage
          }
        })
        
        const { results, count, next, previous } = response.data
        
        if (refresh || page === 1) {
          this.comments = results
        } else {
          this.comments.push(...results)
        }
        
        this.pagination = {
          ...this.pagination,
          currentPage: page,
          totalItems: count,
          totalPages: Math.ceil(count / this.pagination.itemsPerPage)
        }
        
        this.hasMore = !!next
        
      } catch (error) {
        this.error = error.response?.data?.message || 'Failed to fetch comments'
        console.error('Error fetching comments:', error)
      } finally {
        this.loading = false
      }
    },
    
    async createComment(commentData) {
      this.loading = true
      this.error = null
      
      try {
        const response = await api.post('/comments/', commentData)
        
        // Add the new comment to the beginning of the list
        this.comments.unshift(response.data)
        this.pagination.totalItems += 1
        
        return response.data
        
      } catch (error) {
        this.error = error.response?.data?.message || 'Failed to create comment'
        console.error('Error creating comment:', error)
        throw error
      } finally {
        this.loading = false
      }
    },
    
    async updateComment(id, commentData) {
      this.loading = true
      this.error = null
      
      try {
        const response = await api.put(`/comments/${id}/`, commentData)
        
        const index = this.comments.findIndex(comment => comment.id === id)
        if (index !== -1) {
          this.comments[index] = response.data
        }
        
        return response.data
        
      } catch (error) {
        this.error = error.response?.data?.message || 'Failed to update comment'
        console.error('Error updating comment:', error)
        throw error
      } finally {
        this.loading = false
      }
    },
    
    async deleteComment(id) {
      this.loading = true
      this.error = null
      
      try {
        await api.delete(`/comments/${id}/`)
        
        this.comments = this.comments.filter(comment => comment.id !== id)
        this.pagination.totalItems -= 1
        
      } catch (error) {
        this.error = error.response?.data?.message || 'Failed to delete comment'
        console.error('Error deleting comment:', error)
        throw error
      } finally {
        this.loading = false
      }
    },
    
    async loadMore() {
      if (!this.hasMore || this.loading) return
      
      const nextPage = this.pagination.currentPage + 1
      await this.fetchComments(nextPage, false)
    },
    
    async likeComment(id) {
      try {
        const response = await api.post(`/comments/${id}/like/`)
        
        const index = this.comments.findIndex(comment => comment.id === id)
        if (index !== -1) {
          this.comments[index] = { ...this.comments[index], ...response.data }
        }
        
        return response.data
        
      } catch (error) {
        console.error('Error liking comment:', error)
        throw error
      }
    },
    
    clearComments() {
      this.comments = []
      this.pagination = {
        currentPage: 1,
        totalPages: 1,
        totalItems: 0,
        itemsPerPage: 10
      }
      this.hasMore = true
      this.error = null
    },
    
    clearError() {
      this.error = null
    }
  }
})
