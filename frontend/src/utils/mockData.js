// Mock data for development and testing

export const mockComments = [
  {
    id: 1,
    author: 'John Doe',
    email: 'john@example.com',
    content: 'This is a great article! I really enjoyed reading it and learned a lot of new things.',
    created_at: '2025-10-08T10:30:00Z',
    updated_at: '2025-10-08T10:30:00Z',
    likes: 5
  },
  {
    id: 2,
    author: 'Jane Smith',
    email: 'jane@example.com',
    content: 'I have a different perspective on this topic. While I agree with some points, I think there are other factors to consider.',
    created_at: '2025-10-08T09:15:00Z',
    updated_at: '2025-10-08T09:15:00Z',
    likes: 2
  },
  {
    id: 3,
    author: 'Alex Johnson',
    email: 'alex@example.com',
    content: 'Thanks for sharing this! Could you provide more details about the implementation?',
    created_at: '2025-10-08T08:45:00Z',
    updated_at: '2025-10-08T08:45:00Z',
    likes: 1
  },
  {
    id: 4,
    author: 'Sarah Wilson',
    email: 'sarah@example.com',
    content: 'Excellent work! This solution addresses exactly what I was looking for. The explanation is clear and the examples are helpful.',
    created_at: '2025-10-07T16:20:00Z',
    updated_at: '2025-10-07T16:20:00Z',
    likes: 8
  },
  {
    id: 5,
    author: 'Mike Brown',
    email: 'mike@example.com',
    content: 'I tried implementing this but ran into some issues. Has anyone else experienced similar problems?',
    created_at: '2025-10-07T14:10:00Z',
    updated_at: '2025-10-07T14:10:00Z',
    likes: 0
  }
]

export const mockUsers = [
  {
    id: 1,
    name: 'John Doe',
    email: 'john@example.com',
    avatar: null,
    created_at: '2025-09-15T10:00:00Z'
  },
  {
    id: 2,
    name: 'Jane Smith',
    email: 'jane@example.com',
    avatar: null,
    created_at: '2025-09-10T14:30:00Z'
  }
]

export const mockApiResponses = {
  comments: {
    list: {
      count: 25,
      next: 'http://localhost:8000/api/comments/?page=2',
      previous: null,
      results: mockComments
    },
    create: {
      id: 6,
      author: 'New User',
      email: 'newuser@example.com',
      content: 'This is a new comment!',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      likes: 0
    }
  }
}
