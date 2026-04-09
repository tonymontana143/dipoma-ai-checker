// ToxicShield Universal Popup Script

// Firefox/Chrome compatibility
const browser_api = typeof browser !== 'undefined' ? browser : chrome;

// Элементы DOM
const checkedCountEl = document.getElementById('checkedCount');
const blockedCountEl = document.getElementById('blockedCount');
const toggleSwitch = document.getElementById('toggleSwitch');
const statusIndicator = document.getElementById('statusIndicator');
const thresholdSlider = document.getElementById('thresholdSlider');
const thresholdValue = document.getElementById('thresholdValue');
const apiUrlInput = document.getElementById('apiUrl');
const scanBtn = document.getElementById('scanBtn');
const resetBtn = document.getElementById('resetBtn');

// Текущие настройки
let settings = {
  apiUrl: 'http://localhost:8000/api/check',
  threshold: 0.15,
  enabled: true
};

// Отображение списка найденных токсичных элементов
async function updateToxicList() {
  try {
    const tab = await getTargetTab();
    if (!tab?.id) return;
    
    const response = await browser_api.tabs.sendMessage(tab.id, { action: 'getStats' });
    
    if (!response?.toxicElements || response.toxicElements.length === 0) {
      document.getElementById('toxicElementsList').style.display = 'none';
      document.getElementById('emptyToxicList').style.display = 'block';
      return;
    }
    
    document.getElementById('emptyToxicList').style.display = 'none';
    document.getElementById('toxicElementsList').style.display = 'block';
    
    const container = document.getElementById('toxicElementsList');
    container.innerHTML = ''; // Очищаем старые элементы
    
    // Типы с эмодзи
    const typeEmojis = {
      'username': '👤',
      'comment': '💬',
      'post': '📝',
      'caption': '📸',
      'header': '📌',
      'text': '📄'
    };
    
    // Отображаем элементы в обратном порядке (новые в начале)
    const items = response.toxicElements.slice().reverse();
    items.forEach(item => {
      const itemEl = document.createElement('div');
      itemEl.className = 'toxic-item';
      
      const emoji = typeEmojis[item.type] || '•';
      const typeLabel = item.type.charAt(0).toUpperCase() + item.type.slice(1);
      
      itemEl.innerHTML = `
        <div class="toxic-item-content">
          <div style="margin-bottom: 4px;">
            <span class="toxic-item-type">${emoji} ${typeLabel}</span>
            <span class="toxic-item-time">${item.timestamp}</span>
          </div>
          <div class="toxic-item-text">${escapeHtml(item.text)}</div>
        </div>
        <div class="toxic-item-score">
          <div class="toxic-item-badge">${item.score}%</div>
        </div>
      `;
      
      container.appendChild(itemEl);
    });
    
  } catch (error) {
    // Игнорируем ошибки (вкладка может быть не готова)
    console.log('[Popup] Toxic list update skipped:', error.message);
  }
}

// Функция для экранирования HTML
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Надежное определение целевой вкладки для работы расширения
async function getTargetTab() {
  // lastFocusedWindow устойчивее для popup в Firefox/Chrome
  const tabs = await browser_api.tabs.query({ active: true, lastFocusedWindow: true });
  const tab = tabs?.[0];

  if (!tab?.id || !tab?.url) {
    return null;
  }

  // Работаем только с реальными веб-страницами
  if (!/^https?:\/\//i.test(tab.url)) {
    return null;
  }

  return tab;
}

// Загрузка настроек из storage
async function loadSettings() {
  try {
    const stored = await browser_api.storage.sync.get(['apiUrl', 'threshold', 'enabled', 'checkedCount', 'blockedCount']);
    
    settings.apiUrl = stored.apiUrl || settings.apiUrl;
    settings.threshold = stored.threshold !== undefined ? stored.threshold : settings.threshold;
    settings.enabled = stored.enabled !== undefined ? stored.enabled : settings.enabled;
    
    // Обновление UI
    apiUrlInput.value = settings.apiUrl;
    thresholdSlider.value = Math.round(settings.threshold * 100);
    thresholdValue.textContent = `${Math.round(settings.threshold * 100)}%`;
    
    if (settings.enabled) {
      toggleSwitch.classList.add('active');
      statusIndicator.classList.add('status-active');
      statusIndicator.classList.remove('status-inactive');
    } else {
      toggleSwitch.classList.remove('active');
      statusIndicator.classList.add('status-inactive');
      statusIndicator.classList.remove('status-active');
    }
    
    // Обновление статистики
    checkedCountEl.textContent = stored.checkedCount || 0;
    blockedCountEl.textContent = stored.blockedCount || 0;
    
    console.log('[Popup] Settings loaded:', settings);
  } catch (error) {
    console.error('[Popup] Error loading settings:', error);
  }
}

// Сохранение настроек
async function saveSettings() {
  try {
    await browser_api.storage.sync.set(settings);
    console.log('[Popup] Settings saved:', settings);
    
    // Отправка обновлений на активную вкладку
    const tab = await getTargetTab();
    if (tab?.id) {
      browser_api.tabs.sendMessage(tab.id, {
        action: 'updateSettings',
        settings: settings
      }).catch(err => console.log('[Popup] Tab not ready:', err));
    }
  } catch (error) {
    console.error('[Popup] Error saving settings:', error);
  }
}

// Обновление статистики
async function updateStats() {
  try {
    const tab = await getTargetTab();
    if (!tab?.id) return;
    
    const response = await browser_api.tabs.sendMessage(tab.id, { action: 'getStats' });
    
    if (response) {
      checkedCountEl.textContent = response.checkedCount || 0;
      blockedCountEl.textContent = response.blockedCount || 0;
      
      // Обновление индикатора статуса
      if (response.enabled) {
        statusIndicator.classList.add('status-active');
        statusIndicator.classList.remove('status-inactive');
      } else {
        statusIndicator.classList.add('status-inactive');
        statusIndicator.classList.remove('status-active');
      }
    }
    
    // Обновляем список токсичных элементов
    await updateToxicList();
  } catch (error) {
    // Игнорируем ошибки (вкладка может быть не готова)
    console.log('[Popup] Stats update skipped:', error.message);
  }
}

// Toggle переключатель
toggleSwitch.addEventListener('click', async () => {
  settings.enabled = !settings.enabled;
  
  if (settings.enabled) {
    toggleSwitch.classList.add('active');
    statusIndicator.classList.add('status-active');
    statusIndicator.classList.remove('status-inactive');
  } else {
    toggleSwitch.classList.remove('active');
    statusIndicator.classList.add('status-inactive');
    statusIndicator.classList.remove('status-active');
  }
  
  await saveSettings();
});

// Слайдер чувствительности
thresholdSlider.addEventListener('input', (e) => {
  const value = parseInt(e.target.value);
  thresholdValue.textContent = `${value}%`;
  settings.threshold = value / 100;
});

thresholdSlider.addEventListener('change', async () => {
  await saveSettings();
});

// API URL input
apiUrlInput.addEventListener('change', async (e) => {
  settings.apiUrl = e.target.value.trim();
  await saveSettings();
});

// Кнопка сканирования
scanBtn.addEventListener('click', async () => {
  scanBtn.disabled = true;
  scanBtn.textContent = '⏳ Сканирование...';
  
  try {
    const tab = await getTargetTab();
    if (tab?.id) {
      console.log('[Popup] Scan target tab:', tab.id, tab.url);
      await browser_api.tabs.sendMessage(tab.id, { action: 'scan' });
      
      // Обновляем статистику через 1 секунду
      setTimeout(updateStats, 1000);
    } else {
      alert('Откройте обычную веб-страницу (https://...) и попробуйте снова.');
    }
  } catch (error) {
    console.error('[Popup] Scan error:', error);
    alert('Ошибка сканирования. Убедитесь, что страница загружена.');
  } finally {
    scanBtn.disabled = false;
    scanBtn.textContent = '🔍 Сканировать';
  }
});

// Кнопка сброса
resetBtn.addEventListener('click', async () => {
  if (!confirm('Сбросить всю статистику и показать заблокированный контент?')) {
    return;
  }
  
  resetBtn.disabled = true;
  resetBtn.textContent = '⏳ Сброс...';
  
  try {
    const tab = await getTargetTab();
    if (tab?.id) {
      console.log('[Popup] Reset target tab:', tab.id, tab.url);
      await browser_api.tabs.sendMessage(tab.id, { action: 'reset' });
      
      // Сброс локальной статистики
      await browser_api.storage.sync.set({
        checkedCount: 0,
        blockedCount: 0,
        toxicElements: []
      });
      
      checkedCountEl.textContent = '0';
      blockedCountEl.textContent = '0';
      updateToxicList(); // Обновляем список
    }
  } catch (error) {
    console.error('[Popup] Reset error:', error);
  } finally {
    resetBtn.disabled = false;
    resetBtn.textContent = '🔄 Сброс';
  }
});

// Кнопка очистки списка токсичных элементов
document.getElementById('clearListBtn').addEventListener('click', async () => {
  try {
    const tab = await getTargetTab();
    if (tab?.id) {
      await browser_api.tabs.sendMessage(tab.id, { action: 'clearToxicList' });
      updateToxicList(); // Обновляем список
    }
  } catch (error) {
    console.error('[Popup] Clear list error:', error);
  }
});

// Автоматическое обновление статистики каждые 2 секунды
setInterval(updateStats, 2000);

// ===== TABS =====
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    // Remove active from all tabs
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    
    // Activate clicked tab
    btn.classList.add('active');
    const tabId = btn.dataset.tab;
    document.getElementById(`tab-${tabId}`).classList.add('active');
    
    // Update analytics when switching to that tab
    if (tabId === 'analytics') {
      updateAnalytics();
    }
  });
});

// ===== ANALYTICS =====
async function updateAnalytics() {
  try {
    // Get stats from storage
    const stored = await browser_api.storage.sync.get(['checkedCount', 'blockedCount', 'toxicElements']);
    
    const totalScanned = stored.checkedCount || 0;
    const totalToxic = stored.blockedCount || 0;
    const toxicPercent = totalScanned > 0 ? Math.round((totalToxic / totalScanned) * 100) : 0;
    
    document.getElementById('totalScanned').textContent = totalScanned;
    document.getElementById('totalToxic').textContent = totalToxic;
    document.getElementById('toxicPercent').textContent = `${toxicPercent}%`;
    
    // Update toxicity distribution bars
    const toxicElements = stored.toxicElements || [];
    const distribution = { safe: 0, mild: 0, medium: 0, high: 0, critical: 0 };
    
    toxicElements.forEach(item => {
      const score = item.score || 0;
      if (score <= 20) distribution.safe++;
      else if (score <= 40) distribution.mild++;
      else if (score <= 60) distribution.medium++;
      else if (score <= 80) distribution.high++;
      else distribution.critical++;
    });
    
    const maxCount = Math.max(...Object.values(distribution), 1);
    
    Object.keys(distribution).forEach(key => {
      const count = distribution[key];
      const percent = (count / maxCount) * 100;
      document.getElementById(`bar-${key}`).style.width = `${percent}%`;
      document.getElementById(`count-${key}`).textContent = count;
    });
    
    // Load selection history from localStorage via content script
    await updateSelectionHistory();
    
  } catch (error) {
    console.error('[Popup] Analytics update error:', error);
  }
}

async function updateSelectionHistory() {
  try {
    const tab = await getTargetTab();
    if (!tab?.id) return;
    
    const response = await browser_api.tabs.sendMessage(tab.id, { action: 'getSelectionHistory' });
    
    const container = document.getElementById('selectionHistory');
    
    if (!response?.history || response.history.length === 0) {
      container.innerHTML = '<div class="selection-empty">Выделите текст на странице и нажмите "Проверить"</div>';
      return;
    }
    
    container.innerHTML = response.history.map(item => `
      <div class="selection-item">
        <span class="selection-score ${item.isToxic ? 'toxic' : 'safe'}">${Math.round(item.score * 100)}%</span>
        <span class="selection-text">${escapeHtml(item.text)}</span>
      </div>
    `).join('');
    
  } catch (error) {
    console.log('[Popup] Selection history skipped:', error.message);
  }
}

// Инициализация
loadSettings();
updateStats();

console.log('[Popup] Initialized');
