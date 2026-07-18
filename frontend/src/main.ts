import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import Login from './views/Login.vue'
import Dashboard from './views/Dashboard.vue'
import StudentDetail from './views/StudentDetail.vue'
import { getToken, getMe } from './api'

const routes = [
  { path: '/login', component: Login },
  { path: '/', redirect: '/me' },
  { path: '/me', component: StudentDetail, props: { self: true } },     // 学生看自己
  { path: '/admin', component: Dashboard },                              // 管理员：所有人
  { path: '/student/:id', component: StudentDetail, props: true },       // 管理员看指定学生
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫：未登录去登录页；按角色分流；学生不得越权
router.beforeEach(async (to) => {
  const token = getToken()
  if (to.path === '/login') return token ? '/' : true
  if (!token) return '/login'

  let me
  try {
    me = await getMe()
  } catch {
    return '/login'   // 令牌失效
  }

  if (me.is_admin) {
    // 管理员：落到学生自己页时改去管理台；其余(/admin、/student/:id)放行
    return to.path === '/me' ? '/admin' : true
  }
  // 学生：不能进管理台或看别人，一律回自己页
  if (to.path === '/admin' || to.path.startsWith('/student/')) return '/me'
  return true
})

createApp(App).use(router).mount('#app')
