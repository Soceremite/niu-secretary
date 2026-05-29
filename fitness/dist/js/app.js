// fitness/src/js/app.js
const sectionHost = document.getElementById('section-host');
const networkStatus = document.getElementById('network-status');
const pageKicker = document.getElementById('page-kicker');
const pageTitle = document.getElementById('page-title');

const SECTION_META = {
  dashboard: {
    kicker: 'DAILY DECISION',
    title: '先看恢复、热量和趋势，再决定今天怎么练。',
    init: () => import('./features/dashboard.js').then((mod) => mod.initDashboard())
  },
  assessment: {
    kicker: 'BASELINE REPORT',
    title: '把身体基线量清楚，计划才有边界。',
    init: () => import('./features/assessment.js').then((mod) => mod.initAssessment())
  },
  training: {
    kicker: 'TRAINING LOAD',
    title: '训练要有进展，也要知道什么时候收手。',
    init: () => import('./features/training.js').then((mod) => mod.initTraining())
  },
  nutrition: {
    kicker: 'ENERGY BALANCE',
    title: '记录每一餐，让缺口和蛋白都看得见。',
    init: () => import('./features/nutrition.js').then((mod) => mod.initNutrition())
  },
  recovery: {
    kicker: 'READINESS CHECK',
    title: '恢复状态决定今天是推进、维持，还是降载。',
    init: () => import('./features/recovery.js').then((mod) => mod.initRecovery())
  },
  consult: {
    kicker: 'SAFETY FIRST',
    title: '疼痛和风险先分级，红线问题直接停练。',
    init: () => import('./features/consult.js').then((mod) => mod.initConsult())
  }
};

function setNetworkStatus() {
  const online = navigator.onLine;
  networkStatus.textContent = online ? '在线 · 可以开练' : '离线 · 先记着';
  networkStatus.classList.toggle('online', online);
  networkStatus.classList.toggle('offline', !online);
}

async function loadSection(name) {
  const meta = SECTION_META[name] || SECTION_META.dashboard;
  sectionHost.innerHTML = '<div class="loading-card">正在加载模块，牛秘书在热身...</div>';
  pageKicker.textContent = meta.kicker;
  pageTitle.textContent = meta.title;
  const res = await fetch(`sections/${name}.html`);
  if (!res.ok) throw new Error(`Failed to load section: ${name}`);
  sectionHost.innerHTML = await res.text();
  await meta.init();
  setActiveNav(name);
}

function setActiveNav(name) {
  document.querySelectorAll('.nav-chip').forEach((button) => {
    button.classList.toggle('active', button.dataset.section === name);
  });
}

function bindNavigation() {
  document.querySelectorAll('.nav-chip:not(:disabled)').forEach((button) => {
    button.addEventListener('click', () => {
      const name = button.dataset.section;
      history.replaceState(null, '', `#${name}`);
      loadSection(name).catch(showLoadError);
    });
  });
}

async function registerServiceWorker() {
  if (!('serviceWorker' in navigator)) return;
  try {
    await navigator.serviceWorker.register('./sw.js');
  } catch (error) {
    console.warn('Service worker registration failed', error);
  }
}

function showLoadError(error) {
  console.error(error);
  sectionHost.innerHTML = '<div class="loading-card">模块加载失败。牛秘书说：先刷新，别砸电脑。</div>';
}

window.addEventListener('online', setNetworkStatus);
window.addEventListener('offline', setNetworkStatus);

setNetworkStatus();
bindNavigation();
loadSection(location.hash.replace('#', '') || 'dashboard').catch(showLoadError);
registerServiceWorker();
