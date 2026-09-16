import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/app/stores/auth'

const HomePage = () => import('@/modules/home/HomePage.vue')
const FitnessPage = () => import('@/modules/fitness/FitnessPage.vue')
const SchedulePage = () => import('@/modules/schedule/SchedulePage.vue')
const LeisurePage = () => import('@/modules/leisure/LeisurePage.vue')
const NewsPage = () => import('@/modules/news/NewsPage.vue')
const AdminLogin = () => import('@/modules/admin/AdminLogin.vue')
const AdminDashboard = () => import('@/modules/admin/AdminDashboard.vue')
const AdminResourcePage = () => import('@/modules/admin/AdminResourcePage.vue')
const AdminAIResearchPage = () => import('@/modules/admin/AdminAIResearchPage.vue')
const AdminAIResearchBlogsPage = () => import('@/modules/admin/AdminAIResearchBlogsPage.vue')
const AdminLLMPage = () => import('@/modules/admin/AdminLLMPage.vue')
const AdminLLMUsagePage = () => import('@/modules/admin/AdminLLMUsagePage.vue')

const router = createRouter({
  history: createWebHistory('/niu-secretary/'),
  routes: [
    { path: '/', name: 'home', component: HomePage },
    { path: '/fitness/', name: 'fitness', component: FitnessPage },
    { path: '/schedule/', name: 'schedule', component: SchedulePage },
    { path: '/leisure/', name: 'leisure', component: LeisurePage },
    { path: '/news/', name: 'news', component: NewsPage },
    { path: '/admin/login', name: 'admin-login', component: AdminLogin },
    {
      path: '/admin/',
      component: AdminDashboard,
      meta: { requiresAdmin: true },
      children: [
        { path: '', name: 'admin-home', component: AdminResourcePage, props: { resourceKey: 'platform.ops' } },
        { path: 'fitness/nutrition', component: AdminResourcePage, props: { resourceKey: 'fitness.nutrition' } },
        { path: 'fitness/training', component: AdminResourcePage, props: { resourceKey: 'fitness.workouts' } },
        { path: 'fitness/metrics', component: AdminResourcePage, props: { resourceKey: 'fitness.metrics' } },
        { path: 'fitness/assessment', component: AdminResourcePage, props: { resourceKey: 'fitness.assessments' } },
        { path: 'schedule/events', component: AdminResourcePage, props: { resourceKey: 'schedule.events' } },
        { path: 'schedule/todos', component: AdminResourcePage, props: { resourceKey: 'schedule.todos' } },
        { path: 'leisure/items', component: AdminResourcePage, props: { resourceKey: 'leisure.items' } },
        { path: 'leisure/recommendations', component: AdminResourcePage, props: { resourceKey: 'leisure.recommendations' } },
        { path: 'news/topics', component: AdminResourcePage, props: { resourceKey: 'news.recommend' } },
        { path: 'news/recommendations', component: AdminResourcePage, props: { resourceKey: 'news.recommend' } },
        { path: 'airesearch/', component: AdminAIResearchPage, props: { view: 'overview' } },
        { path: 'airesearch/papers', component: AdminAIResearchPage, props: { view: 'papers' } },
        { path: 'airesearch/blogs', component: AdminAIResearchBlogsPage },
        { path: 'airesearch/queue', component: AdminAIResearchPage, props: { view: 'overview' } },
        { path: 'airesearch/discovery', component: AdminAIResearchPage, props: { view: 'search' } },
        { path: 'airesearch/search', component: AdminAIResearchPage, props: { view: 'search' } },
        { path: 'airesearch/profiles', component: AdminAIResearchPage, props: { view: 'profiles' } },
        { path: 'airesearch/review', component: AdminAIResearchPage, props: { view: 'papers' } },
        { path: 'airesearch/pipeline', component: AdminAIResearchPage, props: { view: 'publish' } },
        { path: 'airesearch/publish', component: AdminAIResearchPage, props: { view: 'publish' } },
        { path: 'airesearch/jobs', component: AdminAIResearchPage, props: { view: 'tasks' } },
        { path: 'airesearch/tasks', component: AdminAIResearchPage, props: { view: 'tasks' } },
        { path: 'llm/', name: 'admin-llm', component: AdminLLMPage },
        { path: 'llm/usage', name: 'admin-llm-usage', component: AdminLLMUsagePage }
      ]
    },
    { path: '/:pathMatch(.*)*', redirect: '/' }
  ]
})

router.beforeEach(async (to) => {
  if (!to.meta.requiresAdmin) return true
  const auth = useAuthStore()
  const ok = auth.checked ? auth.authenticated : await auth.verify()
  if (!ok) return { name: 'admin-login', query: { redirect: to.fullPath } }
  return true
})

export default router
