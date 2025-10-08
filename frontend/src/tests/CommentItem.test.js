import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import CommentItem from '../components/CommentItem.vue'

const mockComment = {
  id: 1,
  author: 'Test User',
  email: 'test@example.com',
  content: 'This is a test comment',
  created_at: '2025-10-08T10:00:00Z',
  updated_at: '2025-10-08T10:00:00Z',
  likes: 3
}

describe('CommentItem', () => {
  it('renders comment content correctly', () => {
    const wrapper = mount(CommentItem, {
      props: {
        comment: mockComment
      }
    })

    expect(wrapper.text()).toContain(mockComment.author)
    expect(wrapper.text()).toContain(mockComment.content)
    expect(wrapper.text()).toContain('3')
  })

  it('displays author avatar with first letter', () => {
    const wrapper = mount(CommentItem, {
      props: {
        comment: mockComment
      }
    })

    const avatar = wrapper.find('.author-avatar')
    expect(avatar.text()).toBe('T')
  })

  it('handles like button click', async () => {
    const wrapper = mount(CommentItem, {
      props: {
        comment: mockComment
      }
    })

    const likeButton = wrapper.find('.btn-icon')
    await likeButton.trigger('click')

    expect(wrapper.vm.isLiked).toBe(true)
    expect(likeButton.classes()).toContain('liked')
  })

  it('formats date correctly', () => {
    const wrapper = mount(CommentItem, {
      props: {
        comment: mockComment
      }
    })

    const formattedDate = wrapper.vm.formatDate(mockComment.created_at)
    expect(formattedDate).toContain('2025')
    expect(formattedDate).toContain('October')
  })
})
