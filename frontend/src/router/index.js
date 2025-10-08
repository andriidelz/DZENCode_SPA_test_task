import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Comments from '../views/Comments.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/comments',
    name: 'Comments',
    component: Comments
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
