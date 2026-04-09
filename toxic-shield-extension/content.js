// ToxicShield Universal Content Script
// Сканирует все текстовые элементы на странице и блюрит токсичный контент

// Firefox/Chrome compatibility
const browser_api = typeof browser !== 'undefined' ? browser : chrome;

// Configuration
let config = {
  apiUrl: 'http://localhost:8000/api/check',
  threshold: 0.15,
  enabled: true,
  checkedCount: 0,
  blockedCount: 0
};

// Флаги для защиты от циклического сканирования
let isScanning = false;
let lastScanTime = 0;
const MIN_SCAN_INTERVAL = 1500; // Минимум 1.5 секунды между сканами

// Флаг что кэш уже восстановлен для текущей страницы
let cacheRestored = false;

// Cache для избежания повторных проверок
const toxicityCache = new Map();
const inFlightToxicityChecks = new Map();
let processedElements = new WeakSet();

// Кэш заблюренных элементов по URL (чтобы не пересканивать при возврате)
let scannedUrls = {}; // { url: { hash: true, ... } }

// Список найденных токсичных элементов
let toxicElements = [];

// Кэш токсичных хэшей для повторного применения блюра при виртуальном скроллинге
// { hash -> { score, type, text } }
const toxicHashCache = new Map();

// Дебаунс для scroll handler
let scrollDebounceTimer = null;

// Сканируем только на активной (видимой) вкладке.
// Это убирает лишние запросы с фоновых табов и снижает 429.
function isActiveVisibleTab() {
  return document.visibilityState === 'visible';
}

// Простой хеш для текста (для отслеживания заблюренных элементов)
function simpleHash(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32bit integer
  }
  return Math.abs(hash).toString(16);
}

function normalizeTextForKey(text) {
  return (text || '').toLowerCase().replace(/\s+/g, ' ').trim();
}

function isWhatsAppWeb() {
  return /web\.whatsapp\.com$/i.test(window.location.hostname);
}

function getMinTextLengthForCurrentSite() {
  // В WhatsApp много коротких реплик ("ок", "идиот", "фу" и т.д.)
  return isWhatsAppWeb() ? 3 : 10;
}

function isExtensionUiElement(el) {
  if (!el || typeof el.closest !== 'function') return false;
  return Boolean(
    el.closest('#toxicshield-scan-hud') ||
    el.closest('.toxicshield-scan-hud') ||
    el.closest('#toxicshield-selection-tooltip') ||
    el.closest('.toxicshield-selection-tooltip') ||
    el.closest('.toxic-overlay')
  );
}

// Загрузка настроек из storage
async function loadSettings() {
  try {
    const settings = await browser_api.storage.sync.get(['apiUrl', 'threshold', 'enabled', 'checkedCount', 'blockedCount', 'toxicElements']);
    config.apiUrl = settings.apiUrl || config.apiUrl;
    config.threshold = settings.threshold !== undefined ? settings.threshold : config.threshold;
    config.enabled = settings.enabled !== undefined ? settings.enabled : config.enabled;
    config.checkedCount = settings.checkedCount || 0;
    config.blockedCount = settings.blockedCount || 0;
    toxicElements = settings.toxicElements || []; // Загружаем сохраненный список
    console.log('[ToxicShield] Settings loaded:', config);
  } catch (error) {
    console.error('[ToxicShield] Error loading settings:', error);
  }
}

// Восстановление заблюренных элементов с предыдущего сканирования
function restoreBlurredElements() {
  // Восстанавливаем только один раз за сессию
  if (cacheRestored) {
    return;
  }
  
  const pageUrl = window.location.href;
  
  // Загружаем кэш заблюренных элементов с localStorage
  try {
    const cachedData = localStorage.getItem('toxicshield_blurred_' + pageUrl);
    if (cachedData) {
      const blurCache = JSON.parse(cachedData);
      console.log('[ToxicShield] Restoring blurred elements from cache...', Object.keys(blurCache).length, 'items');
      
      // Восстанавливаем заблюренные элементы
      const elements = getTextElements();
      let restored = 0;
      for (const element of elements) {
        const text = getCleanText(element);
        if (!text) continue;
        
        const textHash = simpleHash(text);
        if (blurCache[textHash]) {
          const { score, type } = blurCache[textHash];
          applyBlurWithoutCheck(element, score, type, text);
          restored++;
        }
      }
      
      console.log(`[ToxicShield] ✅ Restored ${restored} blurred elements from cache`);
      cacheRestored = true; // Отмечаем что кэш восстановлен
    }
  } catch (error) {
    console.error('[ToxicShield] Error restoring blur cache:', error);
  }
}

// Применение блюра без повторной проверки (для восстановления из кэша)
function applyBlurWithoutCheck(element, toxicityScore, elementType, text) {
  const target = pickBestBlurTarget(element);
  if (!target) return;
  
  // Если overlay уже есть - пропускаем
  if (target.querySelector('.toxic-overlay')) return;
  
  // Если уже заблюрен и имеет overlay - пропускаем
  if (target.classList.contains('toxic-blurred') && target.querySelector('.toxic-overlay')) {
    return;
  }

  const rect = target.getBoundingClientRect();
  const viewportArea = Math.max(window.innerWidth * window.innerHeight, 1);
  const targetArea = rect.width * rect.height;

  if (targetArea > viewportArea * 0.35) {
    return;
  }

  processedElements.add(target);
  if (target !== element) processedElements.add(element);
  
  // Добавляем в кэш для виртуального скроллинга
  const textHash = simpleHash(normalizeTextForKey(text));
  if (!toxicHashCache.has(textHash)) {
    toxicHashCache.set(textHash, {
      score: toxicityScore,
      type: elementType,
      text: text
    });
  }

  // Добавляем класс для стилизации
  target.classList.add('toxic-blurred');
  
  // Создаем overlay с кнопкой toggle
  const overlay = document.createElement('div');
  overlay.className = 'toxic-overlay';
  overlay.setAttribute('data-hash', textHash);
  overlay.setAttribute('data-toxic', 'true');
  
  const scorePercent = Math.round(toxicityScore * 100);
  overlay.innerHTML = `<button class="toxic-toggle-btn" title="Нажмите чтобы показать/скрыть">⚠ ${scorePercent}%</button>`;
  
  // Обработчик клика для toggle показа/скрытия
  const toggleBtn = overlay.querySelector('.toxic-toggle-btn');
  let isRevealed = false;
  
  toggleBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    isRevealed = !isRevealed;
    
    if (isRevealed) {
      target.classList.remove('toxic-blurred');
      target.classList.add('toxic-revealed');
      target.querySelectorAll('.toxic-blurred').forEach((el) => {
        el.classList.remove('toxic-blurred');
        el.classList.add('toxic-revealed');
      });
      toggleBtn.classList.add('revealed');
      toggleBtn.setAttribute('title', 'Скрыть токсичный контент');
    } else {
      target.classList.add('toxic-blurred');
      target.classList.remove('toxic-revealed');
      target.querySelectorAll('.toxic-revealed').forEach((el) => {
        el.classList.remove('toxic-revealed');
        el.classList.add('toxic-blurred');
      });
      toggleBtn.classList.remove('revealed');
      toggleBtn.setAttribute('title', 'Показать токсичный контент');
    }
  });

  const computedPosition = window.getComputedStyle(target).position;
  if (computedPosition === 'static') {
    target.style.position = 'relative';
  }
  
  // Исправляем overflow на родителях (для WhatsApp и подобных)
  target.style.overflow = 'visible';
  let parent = target.parentElement;
  for (let i = 0; i < 3 && parent; i++) {
    const parentOverflow = window.getComputedStyle(parent).overflow;
    if (parentOverflow === 'hidden' || parentOverflow === 'clip') {
      parent.style.overflow = 'visible';
    }
    parent = parent.parentElement;
  }
  
  target.appendChild(overlay);
}

// Сохранение статистики
async function saveStats() {
  try {
    await browser_api.storage.sync.set({
      checkedCount: config.checkedCount,
      blockedCount: config.blockedCount
    });
  } catch (error) {
    console.error('[ToxicShield] Error saving stats:', error);
  }
}

// Сброс статистики
async function resetStats() {
  config.checkedCount = 0;
  config.blockedCount = 0;
  await saveStats();
}

// Проверка текста на токсичность через API
async function checkToxicity(text) {
  const normalizedText = (text || '').trim().toLowerCase();

  // Проверка кэша
  if (toxicityCache.has(normalizedText)) {
    return toxicityCache.get(normalizedText);
  }

  // Проверка активного запроса (дедупликация параллельных одинаковых запросов)
  if (inFlightToxicityChecks.has(normalizedText)) {
    return inFlightToxicityChecks.get(normalizedText);
  }

  const requestPromise = (async () => {
    try {
      const response = await browser_api.runtime.sendMessage({
        action: 'checkToxicity',
        apiUrl: config.apiUrl,
        text,
        threshold: config.threshold
      });

      if (!response?.success) {
        console.error('[ToxicShield] Background API error:', response?.error || 'Unknown error');
        return { is_toxic: false, toxicity_score: 0 };
      }

      const data = response.data || { is_toxic: false, toxicity_score: 0 };
      config.checkedCount++;
      
      // Кэширование результата
      toxicityCache.set(normalizedText, data);
      
      // Ограничение размера кэша
      if (toxicityCache.size > 1000) {
        const firstKey = toxicityCache.keys().next().value;
        toxicityCache.delete(firstKey);
      }

      return data;
    } catch (error) {
      console.error('[ToxicShield] Check error:', error);
      return { is_toxic: false, toxicity_score: 0 };
    } finally {
      inFlightToxicityChecks.delete(normalizedText);
    }
  })();

  inFlightToxicityChecks.set(normalizedText, requestPromise);
  return requestPromise;
}

function getDirectText(element) {
  if (!element) return '';
  return Array.from(element.childNodes)
    .filter((n) => n.nodeType === Node.TEXT_NODE)
    .map((n) => n.textContent?.trim() || '')
    .join(' ')
    .trim();
}

// Извлечение чистого текста для проверки (без смешивания вложенных элементов)
function getCleanText(element) {
  if (!element) return '';
  
  // Пропускаем элементы которые уже содержат overlay (уже проверены)
  if (element.classList.contains('toxic-blurred') || 
      element.classList.contains('toxic-revealed')) {
    return '';
  }
  
  // Клонируем элемент чтобы не изменять оригинал
  const clone = element.cloneNode(true);
  
  // Удаляем overlay из клона
  clone.querySelectorAll('.toxic-overlay').forEach(el => el.remove());
  
  // Сначала пробуем взять только прямой текст
  const directText = Array.from(clone.childNodes)
    .filter((n) => n.nodeType === Node.TEXT_NODE)
    .map((n) => n.textContent?.trim() || '')
    .join(' ')
    .trim();
  
  if (directText && directText.length >= 3) {
    return directText;
  }
  
  // Рекурсивный поиск текста в дочерних элементах (до 3 уровней)
  function findTextInChildren(node, depth = 0) {
    if (depth > 3) return ''; // Ограничение глубины
    
    if (!node || !node.childNodes) return '';
    
    // Сначала проверяем прямой текст
    const nodeDirectText = Array.from(node.childNodes)
      .filter(n => n.nodeType === Node.TEXT_NODE)
      .map(n => n.textContent?.trim() || '')
      .join(' ')
      .trim();
    
    if (nodeDirectText && nodeDirectText.length >= 3) {
      return nodeDirectText;
    }
    
    // Ищем в дочерних элементах
    for (const child of node.childNodes) {
      if (child.nodeType === Node.ELEMENT_NODE) {
        const childText = findTextInChildren(child, depth + 1);
        if (childText && childText.length >= 3) {
          return childText;
        }
      }
    }
    
    return '';
  }
  
  const foundText = findTextInChildren(clone);
  if (foundText) return foundText;
  
  // Fallback — только если элемент простой (не контейнер с несколькими блоками)
  const fallbackText = clone.textContent?.trim();
  if (fallbackText && fallbackText.length >= 3 && fallbackText.length <= 200) {
    // Не берём текст если он содержит несколько строк (это контейнер)
    const lines = fallbackText.split('\n').map(l => l.trim()).filter(l => l.length > 2);
    if (lines.length <= 1) {
      return fallbackText;
    }
  }
  
  return '';
}

// Определение типа элемента
function detectElementType(element) {
  if (!element) return 'text';
  
  const tag = element.tagName.toLowerCase();
  const className = element.className.toString().toLowerCase();
  const id = element.id.toString().toLowerCase();
  
  // Username/author patterns
  if (className.includes('username') || className.includes('author') || 
      id.includes('username') || id.includes('author') || tag === 'a' && element.href?.includes('/')) {
    return 'username';
  }
  
  // Comment patterns
  if (className.includes('comment') || id.includes('comment') || 
      className.includes('message') || id.includes('message')) {
    return 'comment';
  }
  
  // Post/status patterns
  if (className.includes('post') || id.includes('post') || 
      className.includes('status') || className.includes('tweet')) {
    return 'post';
  }
  
  // Caption/description
  if (className.includes('caption') || id.includes('caption') || 
      className.includes('description')) {
    return 'caption';
  }
  
  // Header patterns
  if (['h1', 'h2', 'h3', 'h4', 'h5', 'h6'].includes(tag)) {
    return 'header';
  }
  
  return 'text';
}

function pickBestBlurTarget(element) {
  if (!element) return null;

  const tagsToPrefer = 'span,p,li,blockquote,h1,h2,h3,h4,h5,h6,a,strong,em';
  const candidates = [element, ...element.querySelectorAll(tagsToPrefer)];
  const minTextLen = getMinTextLengthForCurrentSite();

  let best = null;
  let bestArea = Number.POSITIVE_INFINITY;

  for (const candidate of candidates) {
    if (processedElements.has(candidate)) continue;
    if (candidate.classList?.contains('toxic-overlay')) continue;

    // Проверяем прямой текст
    let text = getDirectText(candidate);

    // Если прямого текста нет — проверяем один уровень вложенности
    if (text.length < minTextLen) {
      const clone = candidate.cloneNode(true);
      clone.querySelectorAll('.toxic-overlay').forEach(el => el.remove());
      text = Array.from(clone.childNodes)
        .filter(n => n.nodeType === Node.TEXT_NODE)
        .map(n => n.textContent?.trim() || '')
        .join(' ')
        .trim();
    }

    if (text.length < minTextLen) continue;

    const rect = candidate.getBoundingClientRect();
    if (rect.width < 20 || rect.height < 10) continue;

    const area = rect.width * rect.height;
    if (area < bestArea) {
      bestArea = area;
      best = candidate;
    }
  }

  // Не возвращаем сам элемент как fallback если он слишком большой
  if (!best) {
    const rect = element.getBoundingClientRect();
    const viewportArea = Math.max(window.innerWidth * window.innerHeight, 1);
    if ((rect.width * rect.height) > viewportArea * 0.1) return null;
    return element;
  }

  return best;
}

// Сохранение найденного токсичного элемента
async function saveToxicElement(text, type, score) {
  const normalized = normalizeTextForKey(text);
  if (!normalized) return;
  const hash = simpleHash(normalized);

  const element = {
    text: text.substring(0, 150), // Сохраняем первые 150 символов
    type: type,
    score: Math.round(score * 100),
    count: 1,
    hash,
    timestamp: new Date().toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  };

  // Дедупликация: обновляем существующую запись вместо дублирования
  const existingIdx = toxicElements.findIndex((item) => {
    if (item.hash === hash) return true;
    return normalizeTextForKey(item.text) === normalized;
  });
  if (existingIdx >= 0) {
    const existing = toxicElements[existingIdx];
    const updated = {
      ...existing,
      type: element.type,
      score: Math.max(existing.score || 0, element.score),
      count: (existing.count || 1) + 1,
      timestamp: element.timestamp,
      hash
    };
    toxicElements.splice(existingIdx, 1);
    toxicElements.push(updated);
  } else {
    toxicElements.push(element);
  }
  
  // Ограничиваем до последних 50 элементов
  if (toxicElements.length > 50) {
    toxicElements = toxicElements.slice(-50);
  }
  
  // Сохраняем в storage
  try {
    await browser_api.storage.sync.set({
      toxicElements: toxicElements
    });
  } catch (error) {
    console.error('[ToxicShield] Error saving toxic elements:', error);
  }
}

// Блюр элемента с добавлением overlay
function blurElement(element, toxicityScore) {
  const target = pickBestBlurTarget(element);
  if (!target) {
    return;
  }

  if (processedElements.has(target)) {
    return; // Уже обработан
  }

  const rect = target.getBoundingClientRect();
  const viewportArea = Math.max(window.innerWidth * window.innerHeight, 1);
  const targetArea = rect.width * rect.height;

  // Защита от блюра огромных контейнеров ("весь фрейм")
  if (targetArea > viewportArea * 0.35) {
    console.log('[ToxicShield] Skip oversized blur target:', target.tagName, Math.round(targetArea));
    return;
  }

  // Определяем тип элемента и текст до обновления счетчиков
  const elementType = detectElementType(target);
  const text = getCleanText(target);
  const normalized = normalizeTextForKey(text);
  if (!normalized) return;

  // Регистрируем в кэш заблюренных элементов
  const pageUrl = window.location.href;
  const textHash = simpleHash(normalized);
  if (!scannedUrls[pageUrl]) {
    scannedUrls[pageUrl] = {};
  }

  const isFirstTimeForPage = !scannedUrls[pageUrl][textHash];

  processedElements.add(target);
  if (isFirstTimeForPage) {
    config.blockedCount++;
    saveStats();
  }

  saveToxicElement(text, elementType, toxicityScore);

  scannedUrls[pageUrl][textHash] = {
    score: toxicityScore,
    type: elementType
  };
  
  // Сохраняем в кэш для виртуального скроллинга
  toxicHashCache.set(textHash, {
    score: toxicityScore,
    type: elementType,
    text: text
  });
  
  // Сохраняем в localStorage для восстановления при возврате на страницу
  try {
    const cacheKey = 'toxicshield_blurred_' + pageUrl;
    localStorage.setItem(cacheKey, JSON.stringify(scannedUrls[pageUrl]));
  } catch (error) {
    console.error('[ToxicShield] Error saving to localStorage:', error);
  }

  // Добавляем класс для стилизации
  target.classList.add('toxic-blurred');
  
  // Создаем overlay с кнопкой toggle
  const overlay = document.createElement('div');
  overlay.className = 'toxic-overlay';
  overlay.setAttribute('data-hash', textHash);
  overlay.setAttribute('data-toxic', 'true');
  
  const scorePercent = Math.round(toxicityScore * 100);
  overlay.innerHTML = `<button class="toxic-toggle-btn" title="Нажмите чтобы показать/скрыть">⚠ ${scorePercent}%</button>`;
  
  // Обработчик клика для toggle показа/скрытия
  const toggleBtn = overlay.querySelector('.toxic-toggle-btn');
  let isRevealed = false;
  
  toggleBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    isRevealed = !isRevealed;
    
    if (isRevealed) {
      target.classList.remove('toxic-blurred');
      target.classList.add('toxic-revealed');
      target.querySelectorAll('.toxic-blurred').forEach((el) => {
        el.classList.remove('toxic-blurred');
        el.classList.add('toxic-revealed');
      });
      toggleBtn.classList.add('revealed');
      toggleBtn.setAttribute('title', 'Скрыть токсичный контент');
    } else {
      target.classList.add('toxic-blurred');
      target.classList.remove('toxic-revealed');
      target.querySelectorAll('.toxic-revealed').forEach((el) => {
        el.classList.remove('toxic-revealed');
        el.classList.add('toxic-blurred');
      });
      toggleBtn.classList.remove('revealed');
      toggleBtn.setAttribute('title', 'Показать токсичный контент');
    }
  });

  // Вставляем overlay
  const computedPosition = window.getComputedStyle(target).position;
  if (computedPosition === 'static') {
    target.style.position = 'relative';
  }
  
  // Исправляем overflow на родителях (для WhatsApp и подобных)
  target.style.overflow = 'visible';
  let parent = target.parentElement;
  for (let i = 0; i < 3 && parent; i++) {
    const parentOverflow = window.getComputedStyle(parent).overflow;
    if (parentOverflow === 'hidden' || parentOverflow === 'clip') {
      parent.style.overflow = 'visible';
    }
    parent = parent.parentElement;
  }
  
  target.appendChild(overlay);
}

// Получение всех текстовых элементов на странице
function getTextElements() {
  console.log('[ToxicShield] Method 1: Using CSS selectors...');
  const minTextLen = getMinTextLengthForCurrentSite();
  
  const selectors = [
    // WhatsApp Web (приоритетные селекторы)
    '[data-pre-plain-text] span.selectable-text',
    '[data-pre-plain-text] span.copyable-text',
    '[data-pre-plain-text] div.copyable-text',
    'div.message-in span.selectable-text',
    'div.message-out span.selectable-text',
    'span.selectable-text.copyable-text',

    // Instagram специфичные
    'article span',
    '[role="button"] + span',
    'h1', 'h2',
    'ul li span',
    
    // TikTok
    '[class*="DivCommentItemContainer"]',
    '[class*="SpanText"]',
    
    // Twitter/X
    '[data-testid="tweetText"]',
    '[data-testid="tweet"]',
    
    // Комментарии (общие)
    '[class*="comment"]',
    '[id*="comment"]',
    '[class*="Comment"]',
    '[data-testid*="comment"]',
    
    // Посты и сообщения
    '[class*="post"]',
    '[class*="Post"]',
    '[class*="message"]',
    '[class*="Message"]',
    '[class*="tweet"]',
    '[class*="status"]',
    
    // Контент
    'article',
    '[role="article"]',
    '.content',
    '.text',
    'p',
    
    // Заголовки
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    
    // Списки и цитаты
    'li',
    'blockquote',
    
    // Span и div с текстом
    'span',
    'div'
  ];

  const elements = [];
  const seenElements = new Set();

  for (const selector of selectors) {
    try {
      const found = document.querySelectorAll(selector);
      found.forEach(el => {
        // Исключаем скрипты, стили и уже обработанные элементы
        if (el.tagName === 'SCRIPT' || 
            el.tagName === 'STYLE' ||
            el.closest?.('[contenteditable="true"], [role="textbox"], footer') ||
            el.classList.contains('toxic-overlay') ||
            isExtensionUiElement(el) ||
            seenElements.has(el)) {
          return;
        }

        // Проверяем, что элемент содержит текст
        // Проверяем текст с учётом чистоты (без вложений)
        const text = getCleanText(el);
        if (text && text.length >= minTextLen) {
          seenElements.add(el);
          elements.push(el);
        }
      });
    } catch (e) {
      console.warn('[ToxicShield] Selector error:', selector, e);
    }
  }

  console.log(`[ToxicShield] Method 1 found: ${elements.length} elements`);

  // Если селекторы ничего не нашли - используем универсальный метод
  if (elements.length < 10) {
    console.log('[ToxicShield] Method 2: Using universal TreeWalker (Instagram/SPA fallback)...');
    return getTextElementsUniversal();
  }

  return elements;
}

// Универсальный метод для сложных SPA (Instagram, TikTok и т.д.)
function getTextElementsUniversal() {
  const elements = [];
  const seenElements = new Set();
  const minTextLen = getMinTextLengthForCurrentSite();
  
  // Ищем все элементы с текстом через TreeWalker
  const walker = document.createTreeWalker(
    document.body,
    NodeFilter.SHOW_ELEMENT,
    {
      acceptNode: function(node) {
        // Пропускаем системные элементы
        if (node.tagName === 'SCRIPT' || 
            node.tagName === 'STYLE' ||
            node.tagName === 'NOSCRIPT' ||
            node.tagName === 'IFRAME' ||
            node.closest?.('[contenteditable="true"], [role="textbox"], footer') ||
            node.classList.contains('toxic-overlay') ||
            isExtensionUiElement(node) ||
            node.classList.contains('toxic-blurred')) {
          return NodeFilter.FILTER_REJECT;
        }
        
        // Ищем элементы которые содержат "листовой" текст 
        // (не просто вложенные дочерние элементы с текстом)
        const hasDirectText = Array.from(node.childNodes).some(child => 
          child.nodeType === Node.TEXT_NODE && child.textContent.trim().length > 0
        );
        
        if (hasDirectText) {
          return NodeFilter.FILTER_ACCEPT;
        }
        
        return NodeFilter.FILTER_SKIP;
      }
    }
  );

  let node;
  while (node = walker.nextNode()) {
    if (seenElements.has(node)) continue;
    
    const text = node.textContent?.trim();
    
    // Проверяем длину текста
    if (text && text.length >= minTextLen && text.length <= 5000) {
      // Проверяем что это не просто контейнер с вложенными элементами
      const childText = Array.from(node.childNodes)
        .filter(n => n.nodeType === Node.TEXT_NODE)
        .map(n => n.textContent.trim())
        .join(' ')
        .trim();
      
      if (childText.length >= minTextLen) {
        seenElements.add(node);
        elements.push(node);
      }
    }
  }
  
  console.log(`[ToxicShield] Method 2 found: ${elements.length} elements`);
  
  return elements;
}

// =======================
// SCAN VISUALIZATION (HUD)
// =======================
let scanHudElement = null;
let scanHudHideTimer = null;

function ensureScanHud() {
  if (scanHudElement && document.body.contains(scanHudElement)) {
    return scanHudElement;
  }

  scanHudElement = document.createElement('div');
  scanHudElement.id = 'toxicshield-scan-hud';
  scanHudElement.className = 'toxicshield-scan-hud';
  scanHudElement.innerHTML = `
    <div class="toxicshield-scan-title">🛡️ ToxicShield</div>
    <div class="toxicshield-scan-status">Подготовка…</div>
    <div class="toxicshield-scan-progressbar">
      <div class="toxicshield-scan-progressbar-fill"></div>
    </div>
    <div class="toxicshield-scan-meta">
      <span class="toxicshield-scan-progress">0 / 0</span>
      <span class="toxicshield-scan-toxic">Токсичных: 0</span>
    </div>
    <div class="toxicshield-scan-list"></div>
  `;

  document.body.appendChild(scanHudElement);
  return scanHudElement;
}

// Список последних найденных токсичных текстов для HUD
let recentToxicTexts = [];

function addToxicToHud(text, score) {
  const normalized = normalizeTextForKey(text);
  if (!normalized) return;
  const hash = simpleHash(normalized);

  const preview = text.length > 40 ? text.substring(0, 40) + '…' : text;
  const scorePercent = Math.round(score * 100);

  const existingIdx = recentToxicTexts.findIndex((item) => item.hash === hash);
  if (existingIdx >= 0) {
    const existing = recentToxicTexts[existingIdx];
    recentToxicTexts.splice(existingIdx, 1);
    recentToxicTexts.unshift({
      ...existing,
      preview,
      scorePercent: Math.max(existing.scorePercent || 0, scorePercent),
      count: (existing.count || 1) + 1,
      hash
    });
  } else {
    recentToxicTexts.unshift({ preview, scorePercent, count: 1, hash });
  }

  // Храним только последние 5
  if (recentToxicTexts.length > 5) {
    recentToxicTexts = recentToxicTexts.slice(0, 5);
  }
}

function updateScanHud({ status, processed, total, toxicFound }) {
  const hud = ensureScanHud();
  if (!hud) return;

  if (scanHudHideTimer) {
    clearTimeout(scanHudHideTimer);
    scanHudHideTimer = null;
  }

  const safeTotal = Math.max(total || 0, 1);
  const percent = Math.min(100, Math.max(0, Math.round(((processed || 0) / safeTotal) * 100)));

  const statusNode = hud.querySelector('.toxicshield-scan-status');
  const progressNode = hud.querySelector('.toxicshield-scan-progress');
  const toxicNode = hud.querySelector('.toxicshield-scan-toxic');
  const barNode = hud.querySelector('.toxicshield-scan-progressbar-fill');
  const listNode = hud.querySelector('.toxicshield-scan-list');

  if (statusNode) statusNode.textContent = status || 'Сканирование…';
  if (progressNode) progressNode.textContent = `${processed || 0} / ${total || 0}`;
  if (toxicNode) toxicNode.textContent = `Токсичных: ${toxicFound || 0}`;
  if (barNode) barNode.style.width = `${percent}%`;
  
  // Обновляем список токсичных
  if (listNode && recentToxicTexts.length > 0) {
    listNode.innerHTML = recentToxicTexts.map(item => 
      `<div class="toxicshield-scan-item">` +
      `<span class="toxicshield-scan-item-score">${item.scorePercent}%</span>` +
      `<span class="toxicshield-scan-item-text">${escapeHtml(item.preview)}${item.count > 1 ? ` <b>×${item.count}</b>` : ''}</span>` +
      `</div>`
    ).join('');
  } else if (listNode) {
    listNode.innerHTML = '';
  }

  hud.classList.add('is-visible');
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function hideScanHud(delayMs = 1200) {
  if (!scanHudElement) return;

  if (scanHudHideTimer) {
    clearTimeout(scanHudHideTimer);
  }

  scanHudHideTimer = setTimeout(() => {
    scanHudElement?.classList.remove('is-visible');
  }, delayMs);
}

function pulseScanTarget(element) {
  if (!element || !element.classList) return;
  element.classList.add('toxic-scan-target');
  setTimeout(() => {
    element.classList.remove('toxic-scan-target');
  }, 350);
}

// Сканирование страницы
async function scanPage() {
  if (!isActiveVisibleTab()) {
    // Не сканируем фоновые вкладки
    return;
  }

  if (!config.enabled) {
    console.log('[ToxicShield] Scanner disabled');
    return;
  }

  // Защита от циклического сканирования
  if (isScanning) {
    console.log('[ToxicShield] ⏳ Scan already in progress, skipping...');
    return;
  }

  const now = Date.now();
  if (now - lastScanTime < MIN_SCAN_INTERVAL) {
    console.log(`[ToxicShield] ⏸️ Scan throttled (${Math.round((MIN_SCAN_INTERVAL - (now - lastScanTime)) / 1000)}s remaining)`);
    return;
  }

  isScanning = true;
  lastScanTime = now;

  try {
    console.log('[ToxicShield] ========================================');
    console.log('[ToxicShield] Starting page scan on:', window.location.href);
    console.log('[ToxicShield] Page title:', document.title);
    console.log('[ToxicShield] ========================================');
    
    // Пробуем восстановить заблюренные элементы из кэша (только один раз)
    if (!cacheRestored) {
      restoreBlurredElements();
    }

    // Новый скан — очищаем live-список HUD, чтобы не копились старые элементы
    recentToxicTexts = [];
    
    updateScanHud({ status: 'Поиск текста на странице…', processed: 0, total: 0, toxicFound: 0 });
    
    const elements = getTextElements();
    console.log(`[ToxicShield] Found ${elements.length} text elements to check`);

    if (elements.length === 0) {
      console.warn('[ToxicShield] ⚠️ No elements found! Page might be using non-standard structure.');
      console.warn('[ToxicShield] Try waiting for page to fully load, then click Scan again.');
      updateScanHud({ status: 'Текст не найден', processed: 0, total: 0, toxicFound: 0 });
      hideScanHud(1800);
      return;
    }

    const maxElementsPerScan = 200; // Увеличено со 120 до 200
    const uniqueTexts = new Set();
    const filteredElements = [];
    let emptyTextCount = 0;
    let duplicateCount = 0;

    for (const element of elements) {
      if (filteredElements.length >= maxElementsPerScan) break;

      const text = getCleanText(element);
      if (!text) {
        emptyTextCount++;
        continue;
      }

      const normalizedText = text.toLowerCase();
      if (uniqueTexts.has(normalizedText)) {
        duplicateCount++;
        continue;
      }

      uniqueTexts.add(normalizedText);
      filteredElements.push(element);
    }

    console.log(`[ToxicShield] Filtering stats:
  - Total found: ${elements.length}
  - Empty text: ${emptyTextCount}
  - Duplicates: ${duplicateCount}
  - To check: ${filteredElements.length}`);

    if (filteredElements.length !== elements.length) {
      console.log(`[ToxicShield] Reduced workload: ${elements.length} → ${filteredElements.length}`);
    }

  let processedCount = 0;
  let skippedCount = 0;
  let toxicFoundCount = 0;
  const uniqueToxicInScan = new Set();
  // ~4 запроса/сек (2 запроса каждые 500мс) => ~240/мин на вкладку,
  // что безопаснее для backend лимита 300/мин.
  const batchSize = 5;
  const interBatchDelayMs = 150;

  updateScanHud({
    status: 'Сканирую контент…',
    processed: 0,
    total: filteredElements.length,
    toxicFound: toxicFoundCount
  });

  for (let i = 0; i < filteredElements.length; i += batchSize) {
    const batch = filteredElements.slice(i, i + batchSize);
    
    await Promise.all(batch.map(async (element) => {
      // Пропускаем уже обработанные (проверяем и element, и его target)
      if (processedElements.has(element)) {
        skippedCount++;
        return;
      }
      // Пропускаем если элемент уже заблюрен (из восстановления кэша)
      if (element.classList?.contains('toxic-blurred') ||
          element.classList?.contains('toxic-revealed') ||
          element.querySelector?.('.toxic-overlay')) {
        processedElements.add(element);
        skippedCount++;
        return;
      }

      const text = getCleanText(element);
      if (!text) return;

      try {
        pulseScanTarget(element);
        const result = await checkToxicity(text);
        processedCount++;

        if (result.is_toxic) {
          const toxicHash = simpleHash(normalizeTextForKey(text));
          if (!uniqueToxicInScan.has(toxicHash)) {
            uniqueToxicInScan.add(toxicHash);
            toxicFoundCount++;
          }
          console.log('[ToxicShield] Toxic content found:', {
            text: text.substring(0, 50) + '...',
            score: result.toxicity_score
          });
          addToxicToHud(text, result.toxicity_score);
          blurElement(element, result.toxicity_score);
        }
      } catch (error) {
        console.error('[ToxicShield] Error processing element:', error);
      }
    }));

    updateScanHud({
      status: 'Сканирую контент…',
      processed: processedCount,
      total: filteredElements.length,
      toxicFound: toxicFoundCount
    });

    // Небольшая задержка между батчами
    if (i + batchSize < filteredElements.length) {
      await new Promise(resolve => setTimeout(resolve, interBatchDelayMs));
    }
  }

  console.log('[ToxicShield] ========================================');
  console.log(`[ToxicShield] ✅ Scan complete!`);
  console.log(`[ToxicShield] Total found: ${elements.length} elements`);
  console.log(`[ToxicShield] Selected for checking: ${filteredElements.length} elements`);
  console.log(`[ToxicShield] Skipped (already checked): ${skippedCount}`);
  console.log(`[ToxicShield] Newly processed: ${processedCount}`);
  console.log(`[ToxicShield] Total checked: ${config.checkedCount}`);
  console.log(`[ToxicShield] Total blocked: ${config.blockedCount}`);
  console.log('[ToxicShield] ========================================');
  updateScanHud({
    status: 'Готово ✅',
    processed: filteredElements.length,
    total: filteredElements.length,
    toxicFound: toxicFoundCount
  });
  hideScanHud(1600);
  await saveStats();
  } catch (error) {
    console.error('[ToxicShield] Scan error:', error);
    updateScanHud({ status: 'Ошибка сканирования', processed: 0, total: 0, toxicFound: 0 });
    hideScanHud(2000);
  } finally {
    isScanning = false;
    console.log('[ToxicShield] Scan locked released');
  }
}

// Наблюдатель за динамическим контентом
let observer = null;

function startObserver() {
  if (observer) {
    observer.disconnect();
  }

  observer = new MutationObserver((mutations) => {
    if (!config.enabled) return;
    if (!isActiveVisibleTab()) return;

    let hasNewContent = false;
    
    for (const mutation of mutations) {
      if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
        // Пропускаем мутации от самого расширения (overlay, HUD и т.д.)
        const hasExternalNode = Array.from(mutation.addedNodes).some(node => {
          if (node.nodeType !== Node.ELEMENT_NODE) return false;
          return (
            !node.classList?.contains('toxic-overlay') &&
            !node.classList?.contains('toxicshield-scan-hud') &&
            node.id !== 'toxicshield-scan-hud'
          );
        });
        if (hasExternalNode) {
          hasNewContent = true;
          break;
        }
      }
    }

    if (hasNewContent) {
      // Дебаунс: проверяем новый контент через 600мс
      clearTimeout(observer.scanTimeout);
      observer.scanTimeout = setTimeout(() => {
        scanPage();
      }, 600);
    }
  });

  observer.observe(document.body, {
    childList: true,
    subtree: true
  });

  console.log('[ToxicShield] MutationObserver started');
}

// Обработчик скролла для восстановления блюра на виртуальных списках (Threads, Twitter и т.д.)
function handleScrollReblur() {
  if (!config.enabled || !isActiveVisibleTab()) return;
  if (toxicHashCache.size === 0) return;
  
  // Находим все текстовые элементы в видимой области
  const elements = getTextElements();
  let reblurredCount = 0;
  
  for (const element of elements) {
    // Пропускаем если уже заблюрено и имеет overlay
    if (element.classList?.contains('toxic-blurred') && element.querySelector?.('.toxic-overlay')) {
      continue;
    }
    // Пропускаем revealed (пользователь специально открыл)
    if (element.classList?.contains('toxic-revealed')) {
      continue;
    }
    
    const text = getCleanText(element);
    if (!text) continue;
    
    const textHash = simpleHash(text);
    
    // Проверяем есть ли этот хэш в кэше токсичных
    if (toxicHashCache.has(textHash)) {
      const cached = toxicHashCache.get(textHash);
      
      // Проверяем что это точно тот же текст (коллизии хэшей)
      if (cached.text !== text) continue;
      
      // Проверяем что нет overlay (не был уже обработан)
      if (element.querySelector?.('.toxic-overlay')) continue;
      
      const target = pickBestBlurTarget(element);
      if (!target) continue;
      if (target.querySelector('.toxic-overlay')) continue;
      
      console.log('[ToxicShield] Re-applying blur after scroll:', text.substring(0, 30) + '...');
      applyBlurWithoutCheck(element, cached.score, cached.type, text);
      reblurredCount++;
    }
  }
  
  if (reblurredCount > 0) {
    console.log(`[ToxicShield] Re-blurred ${reblurredCount} elements after scroll`);
  }
}

// Запуск слушателя скролла
function startScrollListener() {
  window.addEventListener('scroll', () => {
    if (scrollDebounceTimer) {
      clearTimeout(scrollDebounceTimer);
    }
    scrollDebounceTimer = setTimeout(() => {
      handleScrollReblur();
    }, 300); // Дебаунс 300мс
  }, { passive: true });
  
  console.log('[ToxicShield] Scroll listener started for virtual scrolling sites');
}

// Обработчик сообщений от popup
browser_api.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('[ToxicShield] Message received:', message);

  if (message.action === 'scan') {
    scanPage().then(() => {
      sendResponse({ success: true });
    });
    return true; // Async response
  }

  if (message.action === 'reset') {
    resetStats().then(() => {
      // Удаляем все блюры
      document.querySelectorAll('.toxic-blurred').forEach(el => {
        el.classList.remove('toxic-blurred');
      });
      document.querySelectorAll('.toxic-overlay').forEach(el => {
        el.remove();
      });
      processedElements = new WeakSet();
      toxicityCache.clear();
      toxicElements = []; // Очищаем список найденных элементов
      browser_api.storage.sync.set({ toxicElements: [] });
      
      // Очищаем LocalStorage кэш заблюренных элементов
      const pageUrl = window.location.href;
      localStorage.removeItem('toxicshield_blurred_' + pageUrl);
      scannedUrls[pageUrl] = {};
      cacheRestored = false; // Сбрасываем флаг кэша
      
      sendResponse({ success: true });
    });
    return true; // Async response
  }

  if (message.action === 'getStats') {
    sendResponse({
      checkedCount: config.checkedCount,
      blockedCount: config.blockedCount,
      enabled: config.enabled,
      toxicElements: toxicElements
    });
    return true;
  }

  if (message.action === 'clearToxicList') {
    toxicElements = [];
    browser_api.storage.sync.set({ toxicElements: [] });
    sendResponse({ success: true });
    return true;
  }

  if (message.action === 'updateSettings') {
    config.apiUrl = message.settings.apiUrl || config.apiUrl;
    config.threshold = message.settings.threshold !== undefined ? message.settings.threshold : config.threshold;
    config.enabled = message.settings.enabled !== undefined ? message.settings.enabled : config.enabled;
    
    console.log('[ToxicShield] Settings updated:', config);
    sendResponse({ success: true });
    return true;
  }

  if (message.action === 'getSelectionHistory') {
    try {
      const history = JSON.parse(localStorage.getItem('toxicshield_selection_history') || '[]');
      sendResponse({ history: history.slice(0, 20) }); // Возвращаем последние 20
    } catch (e) {
      sendResponse({ history: [] });
    }
    return true;
  }
});

// Отслеживание изменений URL для SPA (Instagram, Twitter, etc.)
let lastUrl = location.href;
function checkUrlChange() {
  if (!isActiveVisibleTab()) {
    return;
  }

  const currentUrl = location.href;
  if (currentUrl !== lastUrl) {
    console.log('[ToxicShield] URL changed:', lastUrl, '→', currentUrl);
    lastUrl = currentUrl;
    cacheRestored = false; // Сбрасываем флаг для новой страницы
    
    // Даём странице время на загрузку нового контента
    setTimeout(() => {
      if (config.enabled) {
        console.log('[ToxicShield] Rescanning page after navigation...');
        scanPage();
      }
    }, 1000);
  }
}

// Проверяем изменения URL каждые 2 секунды (было 500мс, теперь медленнее)
setInterval(checkUrlChange, 2000);

// Когда вкладка снова становится активной/видимой — делаем мягкий перескан.
document.addEventListener('visibilitychange', () => {
  if (!config.enabled) return;
  if (!isActiveVisibleTab()) return;

  setTimeout(() => {
    scanPage();
  }, 250);
});

// ==========================================================================
// ФУНКЦИЯ ПРОВЕРКИ ВЫДЕЛЕННОГО ТЕКСТА
// ==========================================================================
let selectionTooltip = null;

function createSelectionTooltip() {
  if (selectionTooltip) return selectionTooltip;
  
  selectionTooltip = document.createElement('div');
  selectionTooltip.id = 'toxicshield-selection-tooltip';
  selectionTooltip.className = 'toxicshield-selection-tooltip';
  selectionTooltip.innerHTML = `
    <button class="toxicshield-check-btn">🛡️ Проверить</button>
    <div class="toxicshield-result" style="display: none;">
      <span class="toxicshield-result-score"></span>
      <span class="toxicshield-result-label"></span>
    </div>
    <div class="toxicshield-loading" style="display: none;">⏳</div>
  `;
  document.body.appendChild(selectionTooltip);
  
  const checkBtn = selectionTooltip.querySelector('.toxicshield-check-btn');
  checkBtn.addEventListener('click', handleSelectionCheck);
  
  return selectionTooltip;
}

async function handleSelectionCheck(e) {
  e.stopPropagation();
  
  const selection = window.getSelection();
  const text = selection.toString().trim();
  
  if (!text || text.length < 3) return;
  
  const tooltip = createSelectionTooltip();
  const checkBtn = tooltip.querySelector('.toxicshield-check-btn');
  const resultDiv = tooltip.querySelector('.toxicshield-result');
  const loadingDiv = tooltip.querySelector('.toxicshield-loading');
  const scoreSpan = tooltip.querySelector('.toxicshield-result-score');
  const labelSpan = tooltip.querySelector('.toxicshield-result-label');
  
  checkBtn.style.display = 'none';
  loadingDiv.style.display = 'block';
  resultDiv.style.display = 'none';
  
  try {
    const result = await checkToxicity(text);
    const scorePercent = Math.round(result.toxicity_score * 100);
    
    loadingDiv.style.display = 'none';
    resultDiv.style.display = 'flex';
    scoreSpan.textContent = `${scorePercent}%`;
    
    if (result.is_toxic) {
      scoreSpan.className = 'toxicshield-result-score toxic';
      labelSpan.textContent = 'Токсично';
      labelSpan.className = 'toxicshield-result-label toxic';
    } else {
      scoreSpan.className = 'toxicshield-result-score safe';
      labelSpan.textContent = 'Безопасно';
      labelSpan.className = 'toxicshield-result-label safe';
    }
    
    // Сохраняем в аналитику
    saveSelectionCheck(text, result.toxicity_score, result.is_toxic);
    
  } catch (error) {
    console.error('[ToxicShield] Selection check error:', error);
    loadingDiv.style.display = 'none';
    checkBtn.style.display = 'block';
  }
}

function saveSelectionCheck(text, score, isToxic) {
  // Сохраняем историю проверок выделенного текста
  try {
    const history = JSON.parse(localStorage.getItem('toxicshield_selection_history') || '[]');
    history.unshift({
      text: text.substring(0, 100),
      score,
      isToxic,
      timestamp: Date.now(),
      url: window.location.href
    });
    // Храним последние 50 проверок
    if (history.length > 50) history.length = 50;
    localStorage.setItem('toxicshield_selection_history', JSON.stringify(history));
  } catch (e) {
    console.error('[ToxicShield] Error saving selection history:', e);
  }
}

function showSelectionTooltip(x, y) {
  const tooltip = createSelectionTooltip();
  
  // Reset state
  const checkBtn = tooltip.querySelector('.toxicshield-check-btn');
  const resultDiv = tooltip.querySelector('.toxicshield-result');
  const loadingDiv = tooltip.querySelector('.toxicshield-loading');
  
  checkBtn.style.display = 'block';
  resultDiv.style.display = 'none';
  loadingDiv.style.display = 'none';
  
  // Position tooltip
  tooltip.style.left = `${x}px`;
  tooltip.style.top = `${y - 45}px`;
  tooltip.classList.add('visible');
}

function hideSelectionTooltip() {
  if (selectionTooltip) {
    selectionTooltip.classList.remove('visible');
  }
}

// Обработчик выделения текста
document.addEventListener('mouseup', (e) => {
  // Игнорируем клики по самому тултипу
  if (e.target.closest('#toxicshield-selection-tooltip')) return;
  
  setTimeout(() => {
    const selection = window.getSelection();
    const text = selection.toString().trim();
    
    if (text && text.length >= 3 && text.length <= 500) {
      const range = selection.getRangeAt(0);
      const rect = range.getBoundingClientRect();
      const x = rect.left + rect.width / 2;
      const y = rect.top + window.scrollY;
      showSelectionTooltip(x, y);
    } else {
      hideSelectionTooltip();
    }
  }, 10);
});

// Скрываем при клике вне
document.addEventListener('mousedown', (e) => {
  if (!e.target.closest('#toxicshield-selection-tooltip')) {
    hideSelectionTooltip();
  }
});

// Инициализация
async function init() {
  console.log('[ToxicShield] Initializing on:', window.location.href);
  console.log('[ToxicShield] Document title:', document.title);
  await loadSettings();
  
  if (config.enabled) {
    // Ждем загрузки DOM
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => {
        console.log('[ToxicShield] DOM loaded, starting scan...');
        scanPage();
        startObserver();
        startScrollListener();
      });
    } else {
      console.log('[ToxicShield] DOM already loaded, starting scan...');
      await scanPage();
      startObserver();
      startScrollListener();
    }
  } else {
    console.log('[ToxicShield] Extension is disabled');
  }
}

// Запуск
init();
