// ToxicShield Universal Background Service Worker

// Firefox/Chrome compatibility
const browser_api = typeof browser !== 'undefined' ? browser : chrome;

console.log('[ToxicShield Background] Service worker initialized');

// Проверка текста на токсичность (выполняется в background, чтобы обойти CSP страницы)
async function runToxicityCheck({ apiUrl, text, threshold }) {
  const response = await fetch(apiUrl, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      text,
      threshold
    })
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
}

// Установка расширения
browser_api.runtime.onInstalled.addListener((details) => {
  if (details.reason === 'install') {
    console.log('[ToxicShield Background] Extension installed');
    
    // Установка начальных настроек
    browser_api.storage.sync.set({
      apiUrl: 'http://localhost:8000/api/check',
      threshold: 0.15,
      enabled: true,
      checkedCount: 0,
      blockedCount: 0
    });
    
    // Открытие страницы приветствия (опционально)
    // browser_api.tabs.create({ url: 'welcome.html' });
  }
  
  if (details.reason === 'update') {
    console.log('[ToxicShield Background] Extension updated');
  }
});

// Обработка сообщений от content scripts
browser_api.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('[ToxicShield Background] Message received:', message);

  if (message?.action === 'checkToxicity') {
    runToxicityCheck({
      apiUrl: message.apiUrl,
      text: message.text,
      threshold: message.threshold,
    })
      .then((data) => {
        sendResponse({ success: true, data });
      })
      .catch((error) => {
        console.error('[ToxicShield Background] checkToxicity failed:', error);
        sendResponse({
          success: false,
          error: error?.message || 'Unknown background error',
          data: { is_toxic: false, toxicity_score: 0 }
        });
      });

    return true; // Async response
  }

  sendResponse({ success: true });
  return true;
});

// Обработчик обновления вкладок
browser_api.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  // Когда страница полностью загружена
  if (changeInfo.status === 'complete') {
    console.log('[ToxicShield Background] Tab loaded:', tab.url);
  }
});

// Обработчик клика на иконку расширения (опционально)
browser_api.action.onClicked.addListener((tab) => {
  console.log('[ToxicShield Background] Extension icon clicked');
  // По умолчанию открывается popup, но можно переопределить
});
