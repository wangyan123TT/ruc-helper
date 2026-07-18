import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import Login from './views/Login.vue'
import StudentDetail from './views/StudentDetail.vue'
import { getToken, getMe } from './api'

const routes = [
  { path: '/login', component: Login },
  // 首页不再列出所有人：登录后直接进自己的档案
  { path: '/', redirect: '/me' },
  { path: '/me', component: StudentDetail, props: { self: true } },
  { path: '/student/:id', redirect: '/me' },   // 旧链接兜底
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫：没登录去登录页；已登录访问登录页则进主页
router.beforeEach(async (to) => {
  const token = getToken()
  if (to.path === '/login') {
    return token ? '/me' : true
  }
  if (!token) return '/login'
  // 校验令牌是否仍有效（失效则 api 拦截器会清并跳转）
  try {
    await getMe()
    return true
  } catch {
    return '/login'
  }
})

createApp(App).use(router).mount('#app')
