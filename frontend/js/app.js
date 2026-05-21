// ==========================================
// SERVER API CALLS & UI CONTROL
// ==========================================
async function fetchCurrentCount() {
  try {
    const response = await fetch('/api/v2/count/current');
    if (response.ok) {
      const data = await response.json();
      const newCount = data.count;
      
      /* ToDo: 인원수가 변할 때마다 fetchInitialData()가 호출되어 /stats/today와 /stats/weekly를 모두 재요청함.
         카운트 변화가 잦으면 불필요한 네트워크/서버 부하가 커질 수 있으니,
         today stats만 갱신하거나 일정 주기(예: 1~5분)로 별도 갱신하는 등 호출 빈도를 제한 고려해볼 것.*/
      if (currentCount !== newCount) {
        currentCount = newCount;
        animateCounter(currentCount);
        fetchInitialData(); 
      }
    }
  } catch (error) {
    console.error('인원수 데이터 갱신 실패:', error);
  }
}

async function fetchInitialData() {
  try {
    const todayResponse = await fetch('/api/v2/stats/today');
    if (todayResponse.ok) todayHours = await todayResponse.json();

    const weeklyResponse = await fetch('/api/v2/stats/weekly');
    if (weeklyResponse.ok) weeklyStats = await weeklyResponse.json();

    updateHomeStats();
    renderMiniChart();
    updateStatsChart(selectedDay);
  } catch (error) {
    console.error('통계 데이터 로딩 실패:', error);
  }
}

async function fetchDeveloperData() {
  try {
    const response = await fetch('/data/developers.json');
    if (response.ok) {
      versionData = await response.json();
      renderDevCards(); // 데이터를 다 받아온 뒤에 카드를 그립니다!
    }
  } catch (error) {
    console.error('개발자 데이터를 불러오는 데 실패했습니다:', error);
  }
}

function switchTab(tab) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  
  document.getElementById('page-' + tab).classList.add('active');
  document.getElementById('tab-' + tab).classList.add('active');

  if (tab === 'stats') {
    setTimeout(() => updateStatsChart(selectedDay), 50);
  }
}

function selectDay(day) {
  selectedDay = day;
  document.querySelectorAll('.day-btn').forEach(btn => {
    if (btn.dataset.day === day) {
      btn.className = 'day-btn px-4 py-2 rounded-xl text-sm font-semibold bg-brand-600 text-white transition-all';
    } else {
      btn.className = 'day-btn px-4 py-2 rounded-xl text-sm font-semibold bg-white text-gray-600 border border-gray-200 hover:border-brand-300 transition-all';
    }
  });
  updateStatsChart(day);
}

function animateCounter(target) {
  const el = document.getElementById('counter-value');
  const current = parseInt(el.textContent) || 0;
  const diff = target - current;
  if (diff === 0) { el.textContent = target; return; }
  
  const steps = 30;
  const stepVal = diff / steps;
  let step = 0;

  const interval = setInterval(() => {
    step++;
    if (step >= steps) {
      el.textContent = target;
      clearInterval(interval);
    } else {
      el.textContent = Math.round(current + stepVal * step);
    }
  }, 30);
}

function updateCurrentTime() {
  const now = new Date();
  const timeStr = now.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  document.getElementById('current-time').textContent = timeStr;
  document.getElementById('last-update').textContent = timeStr;
}

/* ToDo: 데이터 수신 성공 시점에만 갱신하고, current-time만 1초마다 갱신하도록 분리 */
function updateHomeStats() {
  if (todayHours.length === 0) return;
  const maxCount = Math.max(...todayHours.map(h => h.count));
  const avgCount = Math.round(todayHours.reduce((s, h) => s + h.count, 0) / todayHours.length);
  document.getElementById('today-max').textContent = maxCount + '명';
  document.getElementById('today-avg').textContent = avgCount + '명';
}

// XSS 방어용 문자열 변환 함수
function escapeHTML(str) {
  if (!str) return '';
  return String(str).replace(/[&<>"']/g, function(match) {
    return {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;'
    }[match];
  });
}

// 안전한 URL(http, https)만 허용하는 검증 함수
function getSafeUrl(url) {
  if (!url) return '#';
  const trimmedUrl = String(url).trim();
  
  // URL이 http:// 또는 https:// 로 시작하는지 정규식으로 검사
  if (/^https?:\/\//i.test(trimmedUrl)) {
    return escapeHTML(trimmedUrl); // 안전하면 기존처럼 이스케이프 후 반환
  }
  
  return '#'; // 이상한 스킴(javascript: 등)이면 링크 무효화
}

// 대체 프로필 이미지(SVG) 생성 함수
function getFallbackImage(name) {
  const initial = escapeHTML(name).charAt(0);
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect fill="#6366f1" width="100" height="100"/><text x="50" y="55" font-size="40" text-anchor="middle" fill="white">${initial}</text></svg>`;
  
  // 브라우저 호환성을 위해 안전하게 인코딩
  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
}

function renderDevCards() {
  const container = document.getElementById('dev-sections');
  container.innerHTML = versionData.map(ver => `
    <div class="version-section">
      <div class="flex items-center justify-between border-b border-gray-200 dark:border-gray-700 pb-3 mb-6">
        <div>
          <h3 class="text-xl font-bold text-gray-900 flex items-center gap-2">
            <i data-lucide="git-branch" class="w-5 h-5 text-brand-500"></i>
            ${escapeHTML(ver.version)}
          </h3>
          <p class="text-sm text-gray-500 mt-1">${escapeHTML(ver.description)}</p>
        </div>
        <a href="${getSafeUrl(ver.repoUrl)}" target="_blank" rel="noopener noreferrer" class="flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 hover:bg-gray-200 dark:bg-white/10 dark:hover:bg-white/20 text-gray-700 dark:text-gray-300 rounded-lg text-sm font-medium transition-colors">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-4 h-4"><path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4"/><path d="M9 18c-4.51 2-5-2-7-2"/></svg>
          <span class="hidden sm:inline">레포지토리</span>
        </a>
      </div>
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
        ${ver.developers.map(dev => `
          <a href="${getSafeUrl(dev.github)}" target="_blank" rel="noopener noreferrer" class="block bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden card-hover dev-card group relative">
            <div class="dev-card-header bg-gradient-to-br from-brand-500 to-brand-700 h-20 relative">
              <div class="absolute top-3 right-3 bg-black/20 backdrop-blur-md p-1.5 rounded-full text-white opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                <i data-lucide="external-link" class="w-4 h-4"></i>
              </div>
              <div class="absolute -bottom-10 left-1/2 -translate-x-1/2">
                <div class="w-20 h-20 rounded-full border-4 border-white dark:border-[#1e293b] overflow-hidden shadow-lg group-hover:scale-105 transition-transform duration-300">
                  <img src="${escapeHTML(dev.photo)}" alt="${escapeHTML(dev.name)}" class="w-full h-full object-cover" onerror="this.src=getFallbackImage('${escapeHTML(dev.name)}')" />
                </div>
              </div>
            </div>
            <div class="pt-14 pb-6 px-5 text-center">
              <h3 class="text-lg font-bold text-gray-900 group-hover:text-brand-600 transition-colors">${escapeHTML(dev.name)}</h3>
              <div class="flex flex-wrap items-center justify-center gap-1.5 mt-2">${(dev.role || '').split('&').map(role => `<span class="inline-block px-3 py-0.5 bg-brand-50 text-brand-700 text-xs font-semibold rounded-full">${escapeHTML(role.trim())}</span>`).join('')}</div>
              <div class="mt-4 space-y-2.5 text-left">
                <div class="flex items-center gap-2.5 text-sm">
                  <div class="w-7 h-7 rounded-lg bg-violet-50 flex items-center justify-center flex-shrink-0">
                    <i data-lucide="award" class="w-3.5 h-3.5 text-violet-500"></i>
                  </div>
                  <span class="text-gray-500">${escapeHTML(dev.generation)}</span>
                </div>
                <div class="flex items-center gap-2.5 text-sm">
                  <div class="w-7 h-7 rounded-lg bg-blue-50 flex items-center justify-center flex-shrink-0">
                    <i data-lucide="graduation-cap" class="w-3.5 h-3.5 text-blue-500"></i>
                  </div>
                  <span class="text-gray-500">${escapeHTML(dev.major)}</span>
                </div>
                <div class="flex items-center gap-2.5 text-sm">
                  <div class="w-7 h-7 rounded-lg bg-emerald-50 flex items-center justify-center flex-shrink-0">
                    <i data-lucide="hash" class="w-3.5 h-3.5 text-emerald-500"></i>
                  </div>
                  <span class="text-gray-500">${escapeHTML(dev.studentId)}</span>
                </div>
              </div>
            </div>
          </a>
        `).join('')}
      </div>
    </div>
  `).join('');
  lucide.createIcons();
}

function initDarkMode() {
  if (localStorage.getItem('theme') === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
    document.documentElement.classList.add('dark');
  } else {
    document.documentElement.classList.remove('dark');
  }
}

function toggleDark() {
  document.documentElement.classList.toggle('dark');
  if (document.documentElement.classList.contains('dark')) {
    localStorage.setItem('theme', 'dark');
  } else {
    localStorage.setItem('theme', 'light');
  }
  renderMiniChart();
  updateStatsChart(selectedDay);
}

// ------------------------------------------
// 앱 초기화 구문
// ------------------------------------------
function init() {
  lucide.createIcons();
  initDarkMode();
  
  const currentDayNum = new Date().getDay();
  const dayMapping = { 1: 'mon', 2: 'tue', 3: 'wed', 4: 'thu', 5: 'fri' };

  selectedDay = dayMapping[currentDayNum] || 'mon';

  selectDay(selectedDay);

  fetchDeveloperData();
  fetchInitialData();
  fetchCurrentCount();
  updateCurrentTime();

  setInterval(() => fetchCurrentCount(), 5000);
  setInterval(updateCurrentTime, 1000);
}

document.addEventListener('DOMContentLoaded', init);