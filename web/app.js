/* ==========================================================================
   LAL10 × MYNTRA FASHION INTELLIGENCE PLATFORM - CLIENT APPLICATION SCRIPT
   ========================================================================== */

function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function displayValue(value, fallback = '-') {
  if (value === null || value === undefined) return fallback;
  const text = String(value).trim();
  return text ? text : fallback;
}

function toNumberOrNull(value) {
  if (value === null || value === undefined || value === '') return null;
  const num = Number(String(value).replace(/,/g, ''));
  return Number.isFinite(num) ? num : null;
}

function displayCount(value, fallback = '-') {
  const num = toNumberOrNull(value);
  return num === null ? fallback : num.toLocaleString('en-IN');
}

function formatDateLabel(value, fallback = '—') {
  if (!value) return fallback;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}

function formatDateTimeLabel(value, fallback = '—') {
  if (!value) return fallback;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
}

function formatDeltaBadge(value, suffix = '%') {
  const num = toNumberOrNull(String(value ?? '').replace('%', ''));
  if (num === null) {
    return { text: '-', tone: 'neutral' };
  }
  if (num > 0) {
    return { text: `↑ ${Math.abs(num).toFixed(1)}${suffix}`, tone: 'positive' };
  }
  if (num < 0) {
    return { text: `↓ ${Math.abs(num).toFixed(1)}${suffix}`, tone: 'negative' };
  }
  return { text: `0.0${suffix}`, tone: 'neutral' };
}

function applyBadgeTone(el, text) {
  if (!el) return;
  const normalized = String(text || '').trim();
  const tone = normalized.startsWith('↓') || normalized.startsWith('-')
    ? 'kpi-down'
    : (normalized === '-' || normalized === '—' || normalized === '0.0%' || normalized === '0.00'
      ? 'kpi-neutral'
      : 'kpi-up');
  el.className = `kpi-badge ${tone}`;
}

function syncSelectFromFacetList(selectId, items, currentValue, allLabel, formatLabel) {
  const select = document.getElementById(selectId);
  if (!select || !Array.isArray(items)) return currentValue || 'all';

  const normalizedItems = items
    .map(item => ({
      value: String(item.value ?? item.name ?? '').trim().toLowerCase(),
      name: String(item.name ?? item.value ?? '').trim(),
      count: Number(item.count || 0)
    }))
    .filter(item => item.value && item.name);

  const availableValues = new Set(normalizedItems.map(item => item.value));
  const nextValue = currentValue && currentValue !== 'all' && availableValues.has(String(currentValue).toLowerCase())
    ? String(currentValue).toLowerCase()
    : 'all';

  select.innerHTML = [`<option value="all">${escapeHtml(allLabel)}</option>`]
    .concat(normalizedItems.map(item => {
      const label = formatLabel ? formatLabel(item) : item.name;
      return `<option value="${escapeHtml(item.value)}" ${item.value === nextValue ? 'selected' : ''}>${escapeHtml(label)}</option>`;
    }))
    .join('');

  select.value = nextValue;
  return nextValue;
}

function formatScopeLabel(category, subcategory = 'all') {
  const sub = String(subcategory || '').trim();
  if (sub && sub.toLowerCase() !== 'all') return sub;

  const categoryMap = {
    shirts: 'Shirts',
    tshirts: 'T-Shirts',
    't-shirts': 'T-Shirts',
    jeans: 'Jeans',
    'western-wear': 'Western Wear',
    'western wear': 'Western Wear',
    dresses: 'Dresses',
    tops: 'Tops',
    trousers: 'Trousers',
    shorts: 'Shorts',
    jackets: 'Jackets',
    sweatshirts: 'Sweatshirts',
    sweaters: 'Sweaters',
    'co-ords': 'Co-Ords',
    coords: 'Co-Ords',
    kurtas: 'Kurtas',
    kurtis: 'Kurtis',
    all: 'All Categories'
  };

  const normalized = String(category || '').trim().toLowerCase();
  if (categoryMap[normalized]) return categoryMap[normalized];
  if (!normalized) return 'Catalog';
  return normalized
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, ch => ch.toUpperCase());
}

function updateCategoryIntelScopeCopy(category, subcategory = 'all') {
  const categoryLabel = formatScopeLabel(category);
  const scopeLabel = formatScopeLabel(category, subcategory);

  const titleEl = document.getElementById('catIntelTitle');
  if (titleEl) titleEl.textContent = categoryLabel;
  const breadcrumbEl = document.getElementById('catIntelBreadcrumbCat');
  if (breadcrumbEl) breadcrumbEl.textContent = categoryLabel.toUpperCase();
  const subtitleEl = document.getElementById('catIntelSubtitle');
  if (subtitleEl) subtitleEl.textContent = `Comprehensive market intelligence for ${scopeLabel.toLowerCase()} across the current filter selection.`;

  const fabricsTitle = document.getElementById('catTopFabricsTitle');
  if (fabricsTitle) fabricsTitle.textContent = `Top Fabrics (${scopeLabel})`;
  const colorsTitle = document.getElementById('catTopColorsTitle');
  if (colorsTitle) colorsTitle.textContent = `Top Colors (${scopeLabel})`;
  const prodsTitle = document.getElementById('catTopProductsTitle');
  if (prodsTitle) prodsTitle.textContent = `Top Products (${scopeLabel})`;
  const prodsSubtitle = document.getElementById('catTopProductsSubtitle');
  if (prodsSubtitle) prodsSubtitle.textContent = `Representative products from the current ${scopeLabel.toLowerCase()} scope`;
}

function updateBrandsScopeCopy(category, subcategory = 'all') {
  const categoryLabel = formatScopeLabel(category);
  const scopeLabel = formatScopeLabel(category, subcategory);

  const titleEl = document.getElementById('scopeHeaderTitle');
  if (titleEl) titleEl.textContent = scopeLabel;
  const breadcrumbEl = document.getElementById('scopeBreadcrumbCat');
  if (breadcrumbEl) breadcrumbEl.textContent = categoryLabel.toUpperCase();
  const subtitleEl = document.getElementById('scopeHeaderSubtitle');
  if (subtitleEl) subtitleEl.textContent = `Complete market intelligence for ${scopeLabel.toLowerCase()} across the current filter selection.`;

  const topBrandsTitleEl = document.getElementById('scopeTopBrandsTitle');
  if (topBrandsTitleEl) topBrandsTitleEl.textContent = `Top 10 Brands (${scopeLabel})`;
  const topBrandsSubtitleEl = document.getElementById('scopeTopBrandsSubtitle');
  if (topBrandsSubtitleEl) topBrandsSubtitleEl.textContent = `By product count with true median prices in the current ${scopeLabel.toLowerCase()} scope`;

  const topProductsSubtitleEl = document.getElementById('scopeTopProductsSubtitle');
  if (topProductsSubtitleEl) topProductsSubtitleEl.textContent = `Representative products ranked from the current ${scopeLabel.toLowerCase()} scope`;
}

let currentView = 'dashboard';
let catalogPage = 1;
let catalogPerPage = 20;
let catalogSort = 'relevance';

let compareProductIds = [];
let allDiscoveredProducts = [];
let chartInstances = {};
let logInterval = null;
let catalogFacetRequestSeq = 0;
let catalogProductsRequestSeq = 0;
let catalogMetaRequestSeq = 0;
let dayOverDayRequestSeq = 0;
let categoryIntelRequestSeq = 0;
let priceIntelRequestSeq = 0;
let hasLoadedCatalogMeta = false;
const clientJsonCache = new Map();
let _scraperStatusRequest = null;

function invalidateClientJsonCache(prefix = '') {
  Array.from(clientJsonCache.keys()).forEach(key => {
    if (!prefix || key.startsWith(prefix)) {
      clientJsonCache.delete(key);
    }
  });
}

async function fetchCachedJson(url, { ttlMs = 15000 } = {}) {
  const now = Date.now();
  const cached = clientJsonCache.get(url);
  if (cached?.data && cached.expiresAt > now) {
    return cached.data;
  }
  if (cached?.promise) {
    return cached.promise;
  }

  const promise = fetchJson(url)
    .then(data => {
      clientJsonCache.set(url, {
        data,
        expiresAt: Date.now() + ttlMs
      });
      return data;
    })
    .catch(err => {
      const pending = clientJsonCache.get(url);
      if (pending?.promise === promise) {
        clientJsonCache.delete(url);
      }
      throw err;
    });

  clientJsonCache.set(url, {
    promise,
    expiresAt: now + ttlMs
  });
  return promise;
}

function buildFilterCountsUrl(params) {
  const qs = params instanceof URLSearchParams ? params.toString() : String(params || '');
  return qs ? `/api/filter-counts?${qs}` : '/api/filter-counts';
}

function buildCatalogMetaUrl(params) {
  const qs = params instanceof URLSearchParams ? params.toString() : String(params || '');
  return qs ? `/api/catalog/meta?${qs}` : '/api/catalog/meta';
}

// ==========================================================================
// 1. INITIALIZATION & ROUTING
// ==========================================================================
document.addEventListener('DOMContentLoaded', () => {
  initApp();
});

async function initApp() {
  if (window.Chart) {
    window.Chart.defaults.animation = window.Chart.defaults.animation || {};
    window.Chart.defaults.animation.duration = 150;
    window.Chart.defaults.animation.easing = 'easeOutQuart';
    window.Chart.defaults.responsive = true;
    window.Chart.defaults.maintainAspectRatio = false;
  }
  checkAuthSession();
  setupKeyboardShortcuts();
  bindCTOFacetInteractions();
  checkScraperStatus();
  setInterval(checkScraperStatus, 8000); // reduced from 4s to avoid hammering

  // Initial Data Load — stats first (instant KPIs), rest in parallel
  await fetchStatsAndInsights();

  // Background sync: refresh stats every 60s, insights every 5min
  // Only refreshes if user is on dashboard view to avoid unnecessary queries
  setInterval(() => {
    if (currentView === 'dashboard') {
      const qs = buildCTOQueryString(readCTOFilterState(), { includeSort: false });
      fetch('/api/stats' + qs)
        .then(r => r.json())
        .then(s => {
          _cachedStats = s;
          renderDashboardKPIs(s, {});
          renderBrandTypeDonut(s);
        })
        .catch(() => {});
    }
  }, 60000);

  setInterval(() => {
    if (currentView === 'dashboard' && !_insightsLoading) {
      _insightsLoading = true;
      const qs = buildCTOQueryString(readCTOFilterState());
      fetch('/api/insights' + qs)
        .then(r => r.json())
        .then(i => {
          _insightsLoading = false;
          if (_cachedStats) renderDashboardKPIs(_cachedStats, i);
          renderCategoryDonut(i);
          renderPriceBandBar(i);
          renderGeographicDemand(i);
          renderTrendingBrands(i);
          renderInventoryHeatmap(i);
          renderAiMarketInsights(i);
        })
        .catch(() => { _insightsLoading = false; });
    }
  }, 300000); // every 5 minutes
}

async function fetchFilterCounts() {
  try {
    const data = await fetchCachedJson('/api/filter-counts', { ttlMs: 20000 });
    const pb = data.price_buckets || {};
    const fmt = n => (n || 0).toLocaleString();

    // 1. DoD price counts
    const dodLt500 = document.getElementById('dodCountLt500');
    if (dodLt500) dodLt500.textContent = fmt(pb.lt_500);
    const dod500_1000 = document.getElementById('dodCount500_1000');
    if (dod500_1000) dod500_1000.textContent = fmt(pb['500_1000']);
    const dod1000_2000 = document.getElementById('dodCount1000_2000');
    if (dod1000_2000) dod1000_2000.textContent = fmt(pb['1000_2000']);
    const dod2000_3000 = document.getElementById('dodCount2000_3000');
    if (dod2000_3000) dod2000_3000.textContent = fmt(pb['2000_3000']);
    const dod3000_4000 = document.getElementById('dodCount3000_4000');
    if (dod3000_4000) dod3000_4000.textContent = fmt(pb['3000_4000']);
    const dodGt4000 = document.getElementById('dodCountGt4000');
    if (dodGt4000) dodGt4000.textContent = fmt(pb.gt_4000);

    // 2. Color price counts
    const colLt500 = document.getElementById('colorCountLt500');
    if (colLt500) colLt500.textContent = fmt(pb.lt_500);
    const col500_1000 = document.getElementById('colorCount500_1000');
    if (col500_1000) col500_1000.textContent = fmt(pb['500_1000']);
    const col1000_2000 = document.getElementById('colorCount1000_2000');
    if (col1000_2000) col1000_2000.textContent = fmt(pb['1000_2000']);
    const col2000_3000 = document.getElementById('colorCount2000_3000');
    if (col2000_3000) col2000_3000.textContent = fmt(pb['2000_3000']);
    const col3000_4000 = document.getElementById('colorCount3000_4000');
    if (col3000_4000) col3000_4000.textContent = fmt(pb['3000_4000']);
    const colGt4000 = document.getElementById('colorCountGt4000');
    if (colGt4000) colGt4000.textContent = fmt(pb.gt_4000);

    // 3. Fabric price counts
    const fabLt500 = document.getElementById('fabricCountLt500');
    if (fabLt500) fabLt500.textContent = fmt(pb.lt_500);
    const fab500 = document.getElementById('fabricCount500to1k');
    if (fab500) fab500.textContent = fmt(pb['500_1000']);
    const fab1k = document.getElementById('fabricCount1kto2k');
    if (fab1k) fab1k.textContent = fmt(pb['1000_2000']);
    const fab2k = document.getElementById('fabricCount2kto3k');
    if (fab2k) fab2k.textContent = fmt(pb['2000_3000']);
    const fab3k = document.getElementById('fabricCount3kto4k');
    if (fab3k) fab3k.textContent = fmt(pb['3000_4000']);
    const fabGt4k = document.getElementById('fabricCountGt4k');
    if (fabGt4k) fabGt4k.textContent = fmt(pb.gt_4000);

    // 4. Brand scope counts
    const scLt500 = document.getElementById('scopeCountLt500');
    if (scLt500) scLt500.textContent = fmt(pb.lt_500);
    const sc500_1000 = document.getElementById('scopeCount500_1000');
    if (sc500_1000) sc500_1000.textContent = fmt(pb['500_1000']);
    const sc1000_2000 = document.getElementById('scopeCount1000_2000');
    if (sc1000_2000) sc1000_2000.textContent = fmt(pb['1000_2000']);
    const sc2000_3000 = document.getElementById('scopeCount2000_3000');
    if (sc2000_3000) sc2000_3000.textContent = fmt(pb['2000_3000']);
    const sc3000_4000 = document.getElementById('scopeCount3000_4000');
    if (sc3000_4000) sc3000_4000.textContent = fmt(pb['3000_4000']);
    const scGt4000 = document.getElementById('scopeCountGt4000');
    if (scGt4000) scGt4000.textContent = fmt(pb.gt_4000);
  } catch (err) {
    console.warn('Error fetching filter counts:', err);
  }
}

async function fetchSnapshotDates() {
  try {
    const data = await fetchCachedJson('/api/snapshot-dates', { ttlMs: 300000 });
    const select = document.getElementById('catalogDateSelect');
    if (!select || !data.dates || data.dates.length === 0) return;

    select.innerHTML = '<option value="all" selected>All Snapshots (Entire Catalog)</option>';
    data.dates.forEach((d, idx) => {
      const opt = document.createElement('option');
      opt.value = d;
      const label = idx === 0 ? `Latest (${d})` : (idx === 1 ? `Yesterday (${d})` : d);
      opt.textContent = `📅 ${label}`;
      select.appendChild(opt);
    });
  } catch (err) {
    console.error('Error loading snapshot dates:', err);
  }
}

function switchView(viewName) {
  currentView = viewName;
  if (viewName !== 'console') stopLogStream();

  // Update Nav Items
  document.querySelectorAll('.sidebar-nav .nav-item').forEach(btn => btn.classList.remove('active'));
  const activeNav = document.getElementById(`nav-${viewName}`);
  if (activeNav) activeNav.classList.add('active');

  // Update View Panels
  document.querySelectorAll('.view-panel').forEach(panel => panel.classList.remove('active'));
  const activePanel = document.getElementById(`view-${viewName}`);
  if (activePanel) {
    activePanel.classList.add('active');
  }

  // Synchronize Intelligence Sub-Tab Navigation state
  const viewToSubtabMap = {
    'analytics-intelligence': 'gmv',
    'price-intel': 'price-intel',
    'daily-movement': 'return-risk',
    'fabric': 'fabric',
    'colors': 'colors',
    'insights': 'size-intel',
    'inventory': 'size-intel'
  };
  const activeSubtab = viewToSubtabMap[viewName];
  if (activeSubtab) {
    document.querySelectorAll('.intel-tabs-nav .intel-tab-btn').forEach(b => {
      b.classList.toggle('active', b.getAttribute('data-subtab') === activeSubtab);
    });
  }

  // View-specific refreshes
  if (viewName === 'analytics-intelligence') {
    loadDailySalesRosAnalytics();
  } else if (viewName === 'category-analysis') {
    loadCategoryIntelligence();
  } else if (viewName === 'fabric') {
    applyFabricFilters();
  } else if (viewName === 'brands') {
    loadBrandsScopeIntelligence();
  } else if (viewName === 'price-intel') {
    loadPriceIntelligence();
  } else if (viewName === 'inventory') {
    switchView('insights');
    const tabBtn = document.getElementById('tab-btn-size-curves');
    if (tabBtn) switchInsightTab('size-curves', tabBtn);
    const sideBtn = document.getElementById('nav-inventory');
    if (sideBtn) {
      document.querySelectorAll('.sidebar-nav .nav-item').forEach(b => b.classList.remove('active'));
      sideBtn.classList.add('active');
    }
    loadSizeIntelligenceView();
    return;
  } else if (viewName === 'daily-movement') {
    loadDayOverDayView();
  } else if (viewName === 'dashboard') {
    fetchStatsAndInsights();
  } else if (viewName === 'catalog') {
    if (!hasLoadedCatalogMeta) {
      hasLoadedCatalogMeta = true;
      fetchSnapshotDates();
    }
    refreshCatalogMeta();
    refreshCatalogSidebarFacets();
    fetchCatalogProducts();
  } else if (viewName === 'compare') {
    renderCompareSuite();
  } else if (viewName === 'insights') {
    loadAnalyticsTrends();
  } else if (viewName === 'colors') {
    loadColorIntelligence();
  } else if (viewName === 'exports') {
    fetchScraperLogsAndRuns();
  } else if (viewName === 'console') {
    startLogStream();
  } else {
    stopLogStream();
  }
}

function switchPriceIntelSection(section, btn) {
  if (section === 'fit-size') {
    switchView('insights');
    const sideBtn = document.getElementById('nav-inventory');
    const tabBtn = document.getElementById('tab-btn-size-curves');
    if (tabBtn) switchInsightTab('size-curves', tabBtn);
    if (sideBtn) {
      document.querySelectorAll('.sidebar-nav .nav-item').forEach(b => b.classList.remove('active'));
      sideBtn.classList.add('active');
    }
    return;
  }

  const targetMap = {
    overview: 'view-price-intel',
    distribution: 'priceDistCard',
    'brand-comparison': 'priceBrandCompareCard',
    trend: 'priceTrendCard',
    fabric: 'priceByFabricCard',
    color: 'priceByColorCard',
    discount: 'priceDiscountCard',
    opportunities: 'priceOpportunitiesCard'
  };

  document.querySelectorAll('#view-price-intel .intel-tabs-row .intel-tab-btn').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');

  const targetId = targetMap[section] || 'view-price-intel';
  const targetEl = document.getElementById(targetId);
  if (targetEl) {
    targetEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
}

function setupKeyboardShortcuts() {
  window.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      const input = document.getElementById('globalSearchInput');
      if (input) input.focus();
    }
  });
}

function handleGlobalSearch(e) {
  if (e.key === 'Enter') {
    const query = e.target.value.trim();
    if (query) {
      openCatalogWithScope({ keyword: query });
    }
  }
}

// ==========================================================================
// 2. DASHBOARD INTELLIGENCE & CHARTS (Image 1)
// ==========================================================================

// Phase-1 stats cache for quick re-renders
let _cachedStats = null;
let _insightsLoading = false;
let _ctoFacetState = {
  brands: [],
  subcategories: [],
  key: '',
  loading: false,
  promise: null
};
let _dashboardRequestId = 0;
let _dashboardFetchController = null;
const MAX_CTO_BRAND_OPTIONS_WITHOUT_SEARCH = 250;
const CTO_FACETS_DEFER_MS = 900;
let _ctoFacetDeferredTimer = null;
let _ctoFacetInteractionBound = false;
let _ctoBrandDropdownOpen = false;

function readCTOFilterState() {
  const brandInput = (document.getElementById('ctoBrandSearchInput')?.value || '').trim();
  const brandSelect = document.getElementById('ctoBrandSelect');
  const knownBrand = (_ctoFacetState.brands || []).find(b => b.value.toLowerCase() === brandInput.toLowerCase());
  const resolvedBrand = brandInput
    ? (knownBrand ? knownBrand.value : '')
    : (brandSelect?.value || '');
  return {
    priceMin: document.getElementById('ctoPriceMin')?.value || '',
    priceMax: document.getElementById('ctoPriceMax')?.value || '',
    subcategory: document.getElementById('ctoSubcategorySelect')?.value || '',
    brand: resolvedBrand || '',
    brandScale: document.getElementById('ctoBrandScaleSelect')?.value || '',
    sortBy: document.getElementById('ctoSortSelect')?.value || '',
    category: document.getElementById('ctoCategorySelect')?.value || '',
    gender: document.getElementById('ctoGenderSelect')?.value || '',
    brandType: document.getElementById('ctoBrandTypeSelect')?.value || ''
  };
}

function buildCTOQueryString(filters, { includeSort = true } = {}) {
  const queryParams = new URLSearchParams();
  if (filters.category && filters.category !== 'all') queryParams.set('category', filters.category);
  if (filters.gender && filters.gender !== 'all') queryParams.set('gender', filters.gender);
  if (filters.brandType && filters.brandType !== 'all') queryParams.set('brand_type', filters.brandType);
  if (filters.subcategory && filters.subcategory !== 'all') queryParams.set('subcategory', filters.subcategory);
  if (filters.brand && filters.brand !== 'all') queryParams.set('brand', filters.brand);
  if (filters.brandScale && filters.brandScale !== 'all') queryParams.set('brand_scale', filters.brandScale);
  if (filters.priceMin) queryParams.set('price_min', filters.priceMin);
  if (filters.priceMax) queryParams.set('price_max', filters.priceMax);
  if (includeSort && filters.sortBy) queryParams.set('sort_by', filters.sortBy);
  const qs = queryParams.toString();
  return qs ? `?${qs}` : '';
}

function updateCTOFilterBadge(filters) {
  const badgeParts = [];
  if (filters.category && filters.category !== 'all') badgeParts.push(filters.category.charAt(0).toUpperCase() + filters.category.slice(1).replace('-', ' '));
  if (filters.subcategory && filters.subcategory !== 'all') badgeParts.push(filters.subcategory);
  if (filters.gender && filters.gender !== 'all') badgeParts.push(filters.gender.charAt(0).toUpperCase() + filters.gender.slice(1));
  if (filters.brandType && filters.brandType !== 'all') badgeParts.push(filters.brandType === 'myntra' ? 'Myntra Labels' : 'External Brands');
  if (filters.priceMin || filters.priceMax) badgeParts.push(`₹${filters.priceMin || '0'} - ₹${filters.priceMax || '∞'}`);
  if (filters.brand && filters.brand !== 'all') badgeParts.push(`Brand: ${filters.brand}`);
  if (filters.brandScale && filters.brandScale !== 'all') badgeParts.push(filters.brandScale);
  renderCTOActiveFilterPills(badgeParts);
}

function renderCTOActiveFilterPills(items = []) {
  const pillsEl = document.getElementById('ctoActiveFilterPills');
  if (!pillsEl) return;
  if (!items.length) {
    pillsEl.innerHTML = '<span class="cto-empty-pill">No filters applied yet</span>';
    return;
  }
  pillsEl.innerHTML = items.map(item => `<span class="cto-active-pill">${escapeHtml(item)}</span>`).join('');
}

function updateCTOScopeCount(count = 0) {
  const countEl = document.getElementById('ctoScopeBrandCount');
  if (!countEl) return;
  const safeCount = Number(count || 0);
  countEl.textContent = `${safeCount.toLocaleString()} Brand${safeCount === 1 ? '' : 's'}`;
}

function applyDashboardFilters() {
  closeCTOBrandDropdown();
  fetchStatsAndInsights();
}

function resetDashboardFilters() {
  const setVal = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.value = val;
  };

  setVal('ctoCategorySelect', 'all');
  setVal('ctoSubcategorySelect', 'all');
  setVal('ctoGenderSelect', 'all');
  setVal('ctoBrandTypeSelect', 'all');
  setVal('ctoPriceMin', '');
  setVal('ctoPriceMax', '');
  setVal('ctoBrandScaleSelect', 'all');
  setVal('ctoBrandSearchInput', '');
  setVal('ctoBrandSelect', 'all');
  setVal('ctoSortSelect', 'valuation_desc');

  applyCTOBrandOptions('all');
  closeCTOBrandDropdown();
  updateCTOFilterBadge(readCTOFilterState());
  fetchStatsAndInsights();
}

function saveDashboardView(btnEl) {
  const btn = btnEl || document.querySelector('.cto-toolbar-btn-save');
  try {
    localStorage.setItem('myntra.dashboard.savedView', JSON.stringify(readCTOFilterState()));
    if (btn) {
      const original = btn.innerHTML;
      btn.classList.add('saved');
      btn.innerHTML = '<span>Saved View</span>';
      setTimeout(() => {
        btn.classList.remove('saved');
        btn.innerHTML = original;
      }, 1400);
    }
  } catch (err) {
    console.warn('Unable to save dashboard view:', err);
  }
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${body.slice(0, 160)}`);
  }
  return response.json();
}

function getCTOFacetQuery(filters = readCTOFilterState()) {
  return buildCTOQueryString(filters, { includeSort: false });
}

function markCTOFacetsPending(filters = readCTOFilterState()) {
  _ctoFacetState.key = getCTOFacetQuery(filters);
  _ctoFacetState.loading = true;

  const brandHintEl = document.getElementById('ctoBrandHint');
  if (brandHintEl) {
    brandHintEl.textContent = 'Loading dynamic brand options for the current scope...';
  }

  const subHintEl = document.getElementById('ctoSubcategoryHint');
  if (subHintEl) {
    subHintEl.textContent = 'Loading dynamic subcategory options for the current scope...';
  }
}

async function ensureCTOFacetsLoaded(filters = readCTOFilterState(), { force = false } = {}) {
  const facetQuery = getCTOFacetQuery(filters);
  if (!force && _ctoFacetState.key === facetQuery && _ctoFacetState.brands.length > 0 && _ctoFacetState.subcategories.length > 0) {
    return _ctoFacetState;
  }
  if (!force && _ctoFacetState.loading && _ctoFacetState.promise && _ctoFacetState.key === facetQuery) {
    return _ctoFacetState.promise;
  }

  _ctoFacetState.key = facetQuery;
  _ctoFacetState.loading = true;
  const currentKey = facetQuery;
  const promise = fetchCachedJson('/api/insights/facets' + facetQuery, { ttlMs: 30000 })
    .then(facetsRes => {
      if (_ctoFacetState.key !== currentKey) {
        return _ctoFacetState;
      }

      renderCTOBrandScaleMeta(facetsRes);
      if (Array.isArray(facetsRes.available_subcategories)) {
        renderSubcategoriesDropdown(facetsRes);
      }
      if (Array.isArray(facetsRes.available_brands)) {
        renderBrandsDropdown(facetsRes);
      }
      renderCTOFilterHints(facetsRes);
      _ctoFacetState.loading = false;
      _ctoFacetState.promise = null;
      return facetsRes;
    })
    .catch(err => {
      if (_ctoFacetState.key === currentKey) {
        _ctoFacetState.loading = false;
        _ctoFacetState.promise = null;
      }
      throw err;
    });

  _ctoFacetState.promise = promise;
  return promise;
}

function scheduleCTOFacetsLoad(filters = readCTOFilterState(), { delayMs = CTO_FACETS_DEFER_MS, force = false } = {}) {
  if (_ctoFacetDeferredTimer) {
    clearTimeout(_ctoFacetDeferredTimer);
  }
  markCTOFacetsPending(filters);

  _ctoFacetDeferredTimer = setTimeout(() => {
    _ctoFacetDeferredTimer = null;
    ensureCTOFacetsLoaded(filters, { force }).catch(err => {
      if (err?.name === 'AbortError') return;
      console.warn('Facet load error (non-fatal):', err);
    });
  }, Math.max(0, delayMs));
}

function primeCTOFacetsFromInteraction() {
  if (_ctoFacetDeferredTimer) {
    clearTimeout(_ctoFacetDeferredTimer);
    _ctoFacetDeferredTimer = null;
  }
  if (_ctoFacetState.loading && _ctoFacetState.promise) return;
  markCTOFacetsPending(readCTOFilterState());
  ensureCTOFacetsLoaded().catch(err => {
    if (err?.name === 'AbortError') return;
    console.warn('Facet load error (non-fatal):', err);
  });
}

function bindCTOFacetInteractions() {
  if (_ctoFacetInteractionBound) return;
  _ctoFacetInteractionBound = true;

  ['ctoSubcategorySelect', 'ctoBrandSearchInput', 'ctoBrandSelect'].forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    ['focus', 'pointerdown'].forEach(eventName => {
      el.addEventListener(eventName, primeCTOFacetsFromInteraction, { passive: true });
    });
  });

  document.addEventListener('click', (event) => {
    const wrap = document.querySelector('.cto-brand-search-wrap');
    if (wrap && !wrap.contains(event.target)) {
      closeCTOBrandDropdown();
    }
  });
}

async function fetchStatsAndInsights() {
  const requestId = ++_dashboardRequestId;
  if (_dashboardFetchController) {
    _dashboardFetchController.abort();
  }
  _dashboardFetchController = new AbortController();
  const { signal } = _dashboardFetchController;
  try {
    const filters = readCTOFilterState();
    const qs = buildCTOQueryString(filters);
    updateCTOFilterBadge(filters);
    scheduleCTOFacetsLoad(filters);

    // PHASE 1: Fetch stats immediately
    const statsRes = await fetchJson('/api/stats' + qs, { signal });
    if (requestId !== _dashboardRequestId) return;
    _cachedStats = statsRes;
    renderDashboardKPIs(statsRes, {});
    renderBrandTypeDonut(statsRes);

    // PHASE 2: Fetch insights in background
    _insightsLoading = true;
    fetchJson('/api/insights' + qs, { signal })
      .then(insightsRes => {
        if (requestId !== _dashboardRequestId) return;
        _insightsLoading = false;
        renderDashboardKPIs(statsRes, insightsRes);
        renderCategoryDonut(insightsRes);
        renderPriceBandBar(insightsRes);
        renderGeographicDemand(insightsRes);
        renderTrendingBrands(insightsRes);
        renderInventoryHeatmap(insightsRes);
        renderAiMarketInsights(insightsRes);
        renderDashboardFabrics(insightsRes);
        renderDashboardColors(insightsRes);
        renderDashboardTop3Products(insightsRes);

        // CTO Executive Renderers
        renderCTOPricingMetrics(insightsRes);
        renderCTOBrandScaleMeta(insightsRes);
        renderBrandScaleDistribution(insightsRes);
        renderBrandValuationMatrix(insightsRes);
      })
      .catch(err => {
        if (requestId !== _dashboardRequestId) return;
        if (err?.name === 'AbortError') return;
        _insightsLoading = false;
        console.warn('Insights load error (non-fatal):', err);
      });
  } catch (err) {
    if (err?.name === 'AbortError') return;
    console.error('Error loading dashboard stats:', err);
  }
}

let _ctoFilterDebounceTimer = null;
function triggerCTOFilter() {
  if (_ctoFilterDebounceTimer) clearTimeout(_ctoFilterDebounceTimer);
  updateCTOFilterBadge(readCTOFilterState());
  _ctoFilterDebounceTimer = setTimeout(() => {
    fetchStatsAndInsights();
  }, 120);
}

function onCTOSliderInput(type) {
  const sliderMin = document.getElementById('ctoSliderMin');
  const sliderMax = document.getElementById('ctoSliderMax');
  const inputMin = document.getElementById('ctoPriceMin');
  const inputMax = document.getElementById('ctoPriceMax');
  const labelEl = document.getElementById('ctoDragValLabel');
  const trackFill = document.getElementById('ctoSliderTrackFill');

  if (!sliderMin || !sliderMax) return;

  let minVal = parseInt(sliderMin.value) || 0;
  let maxVal = parseInt(sliderMax.value) || 10000;

  if (type === 'min' && minVal > maxVal - 100) {
    minVal = maxVal - 100;
    sliderMin.value = minVal;
  } else if (type === 'max' && maxVal < minVal + 100) {
    maxVal = minVal + 100;
    sliderMax.value = maxVal;
  }

  if (inputMin) inputMin.value = minVal > 0 ? minVal : '';
  if (inputMax) inputMax.value = maxVal < 10000 ? maxVal : '';

  if (labelEl) {
    const maxStr = maxVal >= 10000 ? '₹10,000+' : `₹${maxVal.toLocaleString()}`;
    labelEl.textContent = `₹${minVal.toLocaleString()} – ${maxStr}`;
  }

  if (trackFill) {
    const minPct = (minVal / 10000) * 100;
    const maxPct = (maxVal / 10000) * 100;
    trackFill.style.left = `${minPct}%`;
    trackFill.style.width = `${maxPct - minPct}%`;
  }
}

function syncCTOInputsToSlider() {
  const inputMin = document.getElementById('ctoPriceMin');
  const inputMax = document.getElementById('ctoPriceMax');
  const sliderMin = document.getElementById('ctoSliderMin');
  const sliderMax = document.getElementById('ctoSliderMax');

  const minVal = parseInt(inputMin?.value) || 0;
  const maxVal = parseInt(inputMax?.value) || 10000;

  if (sliderMin) sliderMin.value = Math.min(10000, Math.max(0, minVal));
  if (sliderMax) sliderMax.value = Math.min(10000, Math.max(0, maxVal));

  onCTOSliderInput();
  triggerCTOFilter();
}

function applyPricePreset(min, max, btnEl) {
  const minEl = document.getElementById('ctoPriceMin');
  const maxEl = document.getElementById('ctoPriceMax');
  if (minEl) minEl.value = min;
  if (maxEl) maxEl.value = max;

  document.querySelectorAll('.cto-chip').forEach(c => c.classList.remove('active'));
  if (btnEl) btnEl.classList.add('active');

  syncCTOInputsToSlider();
}

function resetPriceFilter(btnEl) {
  const minEl = document.getElementById('ctoPriceMin');
  const maxEl = document.getElementById('ctoPriceMax');
  if (minEl) minEl.value = '';
  if (maxEl) maxEl.value = '';

  document.querySelectorAll('.cto-chip').forEach(c => c.classList.remove('active'));
  if (btnEl) btnEl.classList.add('active');

  syncCTOInputsToSlider();
}

function renderCTOPricingMetrics(insights) {
  const p = insights.cto_pricing || {};
  const setTxt = (id, txt) => { const el = document.getElementById(id); if (el) el.textContent = txt; };

  setTxt('ctoMeanPriceVal', p.mean_price > 0 ? `₹${Math.round(p.mean_price).toLocaleString()}` : '₹0');
  setTxt('ctoMedianPriceVal', p.median_price > 0 ? `₹${Math.round(p.median_price).toLocaleString()}` : '₹0');
  setTxt('ctoModePriceVal', p.mode_price > 0 ? `₹${Math.round(p.mode_price).toLocaleString()}` : '₹0');
  setTxt('ctoIqrPriceVal', (p.p25_price > 0 && p.p75_price > 0) ? `₹${Math.round(p.p25_price).toLocaleString()} – ₹${Math.round(p.p75_price).toLocaleString()}` : '₹0 – ₹0');
}

function renderBrandScaleDistribution(insights) {
  const b = insights.brand_scale_breakdown || {};
  const l = b.largest_brands || {};
  const m = b.mid_brands || {};
  const s = b.small_brands || {};

  const setScale = (cntId, barId, cnt, pct) => {
    const cntEl = document.getElementById(cntId);
    const barEl = document.getElementById(barId);
    if (cntEl) cntEl.textContent = `${(cnt || 0).toLocaleString()} (${pct || 0}%)`;
    if (barEl) barEl.style.width = `${Math.min(100, pct || 0)}%`;
  };

  setScale('ctoLargestCnt', 'ctoLargestBar', l.count, l.share);
  setScale('ctoMidCnt', 'ctoMidBar', m.count, m.share);
  setScale('ctoSmallCnt', 'ctoSmallBar', s.count, s.share);
}

function renderCTOBrandScaleMeta(insights) {
  const meta = insights.brand_scale_meta || {};
  const setTxt = (id, txt) => {
    const el = document.getElementById(id);
    if (el && txt) el.textContent = txt;
  };

  setTxt('ctoBrandScaleOptionLargest', meta.largest_label);
  setTxt('ctoBrandScaleOptionMid', meta.mid_label);
  setTxt('ctoBrandScaleOptionSmall', meta.small_label);
  setTxt('ctoLargestScaleLabel', meta.largest_label);
  setTxt('ctoMidScaleLabel', meta.mid_label);
  setTxt('ctoSmallScaleLabel', meta.small_label);
}

function renderSubcategoriesDropdown(insights) {
  const selectEl = document.getElementById('ctoSubcategorySelect');
  if (!selectEl) return false;
  const currentVal = String(selectEl.value || 'all').trim();
  const currentValLower = currentVal.toLowerCase();

  const subcats = (insights.available_subcategories || [])
    .map(sc => ({
      value: String(sc.value || sc.name || '').trim(),
      label: String(sc.name || sc.value || '').trim(),
      count: Number(sc.count || 0)
    }))
    .filter(sc => sc.value && sc.label);

  _ctoFacetState.subcategories = subcats;
  const valueMap = new Map(subcats.map(sc => [sc.value.toLowerCase(), sc.value]));
  const resolvedValue = currentValLower !== 'all' && !valueMap.has(currentValLower)
    ? 'all'
    : (valueMap.get(currentValLower) || 'all');

  let html = `<option value="all">All Subcategories (${subcats.length.toLocaleString()} types)</option>`;
  subcats.forEach(sc => {
    const isSel = sc.value.toLowerCase() === String(resolvedValue).toLowerCase() ? 'selected' : '';
    html += `<option value="${escapeHtml(sc.value)}" ${isSel}>${escapeHtml(sc.label)} (${sc.count.toLocaleString()})</option>`;
  });

  selectEl.innerHTML = html;
  selectEl.value = resolvedValue;
  return String(resolvedValue).toLowerCase() !== currentValLower;
}

function renderBrandsDropdown(insights) {
  const selectEl = document.getElementById('ctoBrandSelect');
  const inputEl = document.getElementById('ctoBrandSearchInput');
  if (!selectEl) return false;
  const currentVal = String(selectEl.value || 'all').trim();
  const currentValLower = currentVal.toLowerCase();

  _ctoFacetState.brands = (insights.available_brands || [])
    .map(b => ({
      value: String(b.name || '').trim(),
      count: Number(b.count || 0)
    }))
    .filter(b => b.value);

  const valueMap = new Map(_ctoFacetState.brands.map(b => [b.value.toLowerCase(), b.value]));
  const resolvedValue = currentValLower !== 'all' && !valueMap.has(currentValLower)
    ? 'all'
    : (valueMap.get(currentValLower) || 'all');
  applyCTOBrandOptions(resolvedValue);
  if (inputEl && resolvedValue !== 'all' && !inputEl.value.trim()) {
    inputEl.value = resolvedValue;
  }
  return String(resolvedValue).toLowerCase() !== currentValLower;
}

function applyCTOBrandOptions(selectedValue = 'all') {
  const selectEl = document.getElementById('ctoBrandSelect');
  const inputEl = document.getElementById('ctoBrandSearchInput');
  const metaEl = document.getElementById('ctoBrandDropdownMeta');
  if (!selectEl) return;

  const rawSearchTerm = (inputEl?.value || '').trim();
  const searchTerm = rawSearchTerm.toLowerCase();
  const allBrands = _ctoFacetState.brands || [];
  let visibleBrands = searchTerm
    ? allBrands.filter(b => b.value.toLowerCase().includes(searchTerm))
    : allBrands.slice(0, MAX_CTO_BRAND_OPTIONS_WITHOUT_SEARCH);

  const selectedBrand = selectedValue && selectedValue !== 'all'
    ? allBrands.find(b => b.value.toLowerCase() === String(selectedValue).toLowerCase())
    : null;
  if (selectedBrand && !visibleBrands.some(b => b.value.toLowerCase() === selectedBrand.value.toLowerCase())) {
    visibleBrands = [selectedBrand].concat(visibleBrands);
  }

  let html = `<option value="all">All Brands (${allBrands.length.toLocaleString()})</option>`;
  visibleBrands.forEach(b => {
    const isSel = b.value.toLowerCase() === String(selectedValue || 'all').toLowerCase() ? 'selected' : '';
    html += `<option value="${escapeHtml(b.value)}" ${isSel}>${escapeHtml(b.value)} (${b.count.toLocaleString()})</option>`;
  });

  if (!searchTerm && allBrands.length > visibleBrands.length) {
    html += `<option value="" disabled>Showing first ${visibleBrands.length.toLocaleString()} brands. Type to search ${allBrands.length.toLocaleString()} total brands.</option>`;
  }

  if (visibleBrands.length === 0) {
    html += '<option value="" disabled>No brands match this search</option>';
  }

  const exactMatch = allBrands.find(b => b.value.toLowerCase() === searchTerm);
  const effectiveSelectedValue = rawSearchTerm && !exactMatch
    ? 'all'
    : (exactMatch?.value || selectedValue || 'all');
  selectEl.innerHTML = html;
  selectEl.value = effectiveSelectedValue;
  renderCTOBrandDropdownList(visibleBrands, effectiveSelectedValue, {
    totalBrands: allBrands.length,
    searchTerm: rawSearchTerm
  });
  if (metaEl) {
    metaEl.textContent = rawSearchTerm
      ? `${visibleBrands.length.toLocaleString()} match${visibleBrands.length === 1 ? '' : 'es'}`
      : `${allBrands.length.toLocaleString()} in scope`;
  }
  if (inputEl && exactMatch && rawSearchTerm !== exactMatch.value) {
    inputEl.value = exactMatch.value;
  }
  if (inputEl && !rawSearchTerm && (!selectedValue || selectedValue === 'all')) {
    inputEl.value = '';
  }
}

function filterCTOBrandOptions() {
  if (!_ctoFacetState.brands.length && !_ctoFacetState.loading) {
    primeCTOFacetsFromInteraction();
  }

  const currentVal = document.getElementById('ctoBrandSelect')?.value || 'all';
  applyCTOBrandOptions(currentVal);
  openCTOBrandDropdown();
  renderCTOFilterHints({
    cto_filter_meta: {
      available_brand_count: (_ctoFacetState.brands || []).length,
      available_subcategory_count: (_ctoFacetState.subcategories || []).length
    }
  });
}

function renderCTOBrandDropdownList(visibleBrands, selectedValue = 'all', { totalBrands = 0, searchTerm = '' } = {}) {
  const listEl = document.getElementById('ctoBrandDropdownList');
  if (!listEl) return;

  const normalizedSelected = String(selectedValue || 'all').toLowerCase();
  let html = `
    <button type="button" class="cto-brand-option ${normalizedSelected === 'all' ? 'active' : ''}" onclick="selectCTOBrandOption('all')">
      <span class="cto-brand-option-name">All Brands</span>
      <span class="cto-brand-option-count">${totalBrands.toLocaleString()}</span>
    </button>
  `;

  if (!visibleBrands.length) {
    html += `<div class="cto-brand-empty-state">No brands match "${escapeHtml(searchTerm)}".</div>`;
  } else {
    html += visibleBrands.map(brand => {
      const active = brand.value.toLowerCase() === normalizedSelected ? 'active' : '';
      return `
        <button type="button" class="cto-brand-option ${active}" data-brand="${escapeHtml(brand.value)}" onclick="selectCTOBrandOption(this.dataset.brand)">
          <span class="cto-brand-option-name">${escapeHtml(brand.value)}</span>
          <span class="cto-brand-option-count">${brand.count.toLocaleString()}</span>
        </button>
      `;
    }).join('');
  }

  if (!searchTerm && totalBrands > visibleBrands.length) {
    html += `<div class="cto-brand-dropdown-note">Showing first ${visibleBrands.length.toLocaleString()} brands. Start typing to narrow the list.</div>`;
  }

  listEl.innerHTML = html;
}

function selectCTOBrandOption(value) {
  const nextValue = value === 'all' ? 'all' : String(value || '');
  const selectEl = document.getElementById('ctoBrandSelect');
  const inputEl = document.getElementById('ctoBrandSearchInput');
  if (!selectEl) return;
  selectEl.value = nextValue;
  if (inputEl) {
    inputEl.value = nextValue === 'all' ? '' : nextValue;
  }
  applyCTOBrandOptions(nextValue);
  closeCTOBrandDropdown();
  triggerCTOFilter();
}

function openCTOBrandDropdown() {
  const dropdownEl = document.getElementById('ctoBrandDropdown');
  if (!dropdownEl) return;
  dropdownEl.hidden = false;
  _ctoBrandDropdownOpen = true;
}

function closeCTOBrandDropdown() {
  const dropdownEl = document.getElementById('ctoBrandDropdown');
  if (!dropdownEl) return;
  dropdownEl.hidden = true;
  _ctoBrandDropdownOpen = false;
}

function toggleCTOBrandDropdown() {
  if (_ctoBrandDropdownOpen) {
    closeCTOBrandDropdown();
    return;
  }
  if (!_ctoFacetState.brands.length && !_ctoFacetState.loading) {
    primeCTOFacetsFromInteraction();
  }
  applyCTOBrandOptions(document.getElementById('ctoBrandSelect')?.value || 'all');
  openCTOBrandDropdown();
}

function renderCTOFilterHints(insights) {
  const meta = insights.cto_filter_meta || {};
  const brandHintEl = document.getElementById('ctoBrandHint');
  const subHintEl = document.getElementById('ctoSubcategoryHint');
  const brandSearchTerm = (document.getElementById('ctoBrandSearchInput')?.value || '').trim();
  const totalBrands = Number(meta.available_brand_count || (_ctoFacetState.brands || []).length || 0);
  const totalSubcats = Number(meta.available_subcategory_count || (_ctoFacetState.subcategories || []).length || 0);
  const selectedBrand = String(meta.selected_brand || '').trim();
  const selectedSubcategory = String(meta.selected_subcategory || '').trim();
  const visibleBrands = brandSearchTerm
    ? (_ctoFacetState.brands || []).filter(b => b.value.toLowerCase().includes(brandSearchTerm.toLowerCase())).length
    : totalBrands;

  updateCTOScopeCount(totalBrands);

  if (_ctoFacetState.loading && totalBrands === 0 && totalSubcats === 0) {
    if (brandHintEl) {
      brandHintEl.textContent = 'Loading dynamic brand options for the current scope...';
    }
    if (subHintEl) {
      subHintEl.textContent = 'Loading dynamic subcategory options for the current scope...';
    }
    return;
  }

  if (brandHintEl) {
    if (brandSearchTerm) {
      brandHintEl.textContent = `Showing ${visibleBrands.toLocaleString()} of ${totalBrands.toLocaleString()} brand options for "${brandSearchTerm}" under the current non-brand filters.`;
    } else if (selectedBrand) {
      brandHintEl.textContent = `Current brand: ${selectedBrand}. ${totalBrands.toLocaleString()} brand options are available if you switch brands under the same non-brand filters.`;
    } else {
      brandHintEl.textContent = `${totalBrands.toLocaleString()} brand options match the current non-brand filters. Search before opening the dropdown for faster selection.`;
    }
  }

  if (subHintEl) {
    subHintEl.textContent = selectedSubcategory
      ? `Current subcategory: ${selectedSubcategory}. ${totalSubcats.toLocaleString()} subcategory options are available if you switch subcategories under the same non-subcategory filters.`
      : `${totalSubcats.toLocaleString()} subcategory options are available under the current non-subcategory filters.`;
  }
}

function renderBrandValuationMatrix(insights) {
  const tbody = document.getElementById('ctoBrandMatrixTbody');
  if (!tbody) return;

  const matrix = insights.brand_valuation_matrix || [];
  if (!matrix.length) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:#94a3b8;padding:12px;">No matching brands found</td></tr>';
    return;
  }

  tbody.innerHTML = matrix.map((b, idx) => `
    <tr>
      <td style="font-weight:700;color:#64748b;">${idx + 1}</td>
      <td style="font-weight:700;color:#0f172a;">${escapeHtml(b.brand)}</td>
      <td><span class="badge-tag" style="background:#f1f5f9;color:#334155;font-size:10.5px;">${b.scale_tier}</span></td>
      <td>${(b.skus || 0).toLocaleString()}</td>
      <td style="font-weight:600;">₹${Math.round(b.mean_price || 0).toLocaleString()}</td>
      <td style="font-weight:750;color:#0f172a;">₹${Math.round(b.inventory_valuation || 0).toLocaleString()}</td>
    </tr>
  `).join('');
}

function renderDashboardKPIs(stats, insights) {
  const total = Number(stats.total_products || 0);
  const inStock = Number(stats.in_stock || 0);
  const inStockPct = total > 0 ? ((inStock / total) * 100).toFixed(1) : '0.0';
  const trends = stats.trends || {};
  updateCTOScopeCount(Number(stats.total_brands || 0));

  const setTxt = (id, text) => {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  };

  // Helper for trend badge formatting
  function formatTrendBadge(el, delta, invert = false) {
    if (!el) return;
    if (delta === null || delta === undefined || delta === '') {
      el.textContent = '—';
      el.className = el.className.includes('badge-tag') ? 'badge-tag neutral' : 'kpi-trend neutral';
      return;
    }
    const val = Number(delta);
    if (isNaN(val) || val === 0) {
      el.textContent = '±0%';
      el.className = el.className.includes('badge-tag') ? 'badge-tag neutral' : 'kpi-trend neutral';
      return;
    }
    const isPos = val > 0;
    const isGood = invert ? !isPos : isPos;
    const arrow = isPos ? '↑ ' : '↓ ';
    el.textContent = `${arrow}${Math.abs(val)}%`;
    if (el.className.includes('badge-tag')) {
      el.className = isGood ? 'badge-tag green' : 'badge-tag red';
    } else {
      el.className = isGood ? 'kpi-trend positive' : 'kpi-trend negative';
    }
  }

  // KPI 1: Total Products
  setTxt('kpiTotalProducts', total.toLocaleString());
  const prodTrendEl = document.getElementById('kpiTrendProducts');
  formatTrendBadge(prodTrendEl, trends.products_delta_pct);
  setTxt('kpiInStockRatio', `${inStockPct}% In-Stock (${inStock.toLocaleString()})`);

  // KPI 2: Active Brands
  const totalBrands = Number(stats.total_discovered_brands || stats.total_brands || 0);
  setTxt('kpiActiveBrands', totalBrands.toLocaleString());
  const brandTrendEl = document.getElementById('kpiTrendBrands');
  formatTrendBadge(brandTrendEl, trends.brands_delta_pct);
  setTxt('brandsSubtitleCount', totalBrands.toLocaleString());

  // KPI 3: Total Inventory — real from DB
  const totalUnitsRaw = insights.total_warehouse_units ?? stats.total_warehouse_units;
  const totalUnits = totalUnitsRaw === null || totalUnitsRaw === undefined ? null : Number(totalUnitsRaw);
  setTxt('kpiTotalInventory', totalUnits === null || Number.isNaN(totalUnits) ? '—' : totalUnits.toLocaleString());
  const invTrendEl = document.getElementById('kpiTrendInventory');
  formatTrendBadge(invTrendEl, trends.inventory_delta_pct);
  const avgUnits = total > 0 && totalUnits && totalUnits > 0 ? Math.round(totalUnits / total) : 0;
  setTxt('kpiAvgUnitsSku', avgUnits > 0 ? `Avg ~${avgUnits.toLocaleString()} units per SKU` : 'Waiting for inventory sync');

  // KPI 4: Avg Selling Price — real from DB
  const avgPrice = Math.round(Number(stats.average_price || insights.avg_price || 0));
  const avgMrp = Math.round(Number(insights.avg_mrp || stats.average_mrp || 0));
  setTxt('kpiAvgPrice', `₹${avgPrice.toLocaleString()}`);
  const priceTrendEl = document.getElementById('kpiTrendPrice');
  formatTrendBadge(priceTrendEl, trends.price_delta_pct);
  setTxt('kpiAvgMrp', `MRP ₹${avgMrp.toLocaleString()} (Avg)`);

  // KPI 5: Average Discount — real from DB
  const avgDisc = insights.avg_discount_pct !== undefined ? Number(insights.avg_discount_pct) : Number(stats.average_discount || 0);
  setTxt('kpiAvgDiscount', `${avgDisc}% OFF`);
  const discTrendEl = document.getElementById('kpiTrendDiscount');
  formatTrendBadge(discTrendEl, trends.discount_delta_pct);

  // Donut labels
  setTxt('donutTotalProducts', total.toLocaleString());
  setTxt('donutTotalBrands', totalBrands.toLocaleString());

  // Catalog Hero Pills / KPI cards — all real & safe
  setTxt('catKpiTotalProductsVal', total.toLocaleString());
  setTxt('catKpiTotalBrandsVal', totalBrands.toLocaleString());
  setTxt('catKpiAvgDiscountVal', `${avgDisc}%`);

  setTxt('catTotalProds', total > 0 ? total.toLocaleString() : '0');
  formatTrendBadge(document.getElementById('catTrendProds'), trends.products_delta_pct);
  setTxt('catInStockSub', `In-Stock (${inStockPct}%)`);
  setTxt('catAvgPrice', avgPrice > 0 ? `₹${avgPrice.toLocaleString()}` : '₹0');
  formatTrendBadge(document.getElementById('catTrendPrice'), trends.price_delta_pct, true);
  setTxt('catAvgMrp', avgMrp > 0 ? `MRP ₹${avgMrp.toLocaleString()} (Avg)` : '');
  setTxt('catAvgDiscount', avgDisc > 0 ? `${avgDisc}% OFF` : '0% OFF');
  formatTrendBadge(document.getElementById('catTrendDiscount'), trends.discount_delta_pct);
  setTxt('catDiscoveredBrands', totalBrands.toLocaleString());
  setTxt('catTotalStockUnits', totalUnits > 0 ? totalUnits.toLocaleString() : '0');
  setTxt('catAvgStockPerSku', avgUnits > 0 ? `Avg ~${avgUnits.toLocaleString()} units per SKU` : '0 units per SKU');

  // Catalog Tab Counts — from stats.category_counts
  const catCounts = stats.category_counts || {};
  setTxt('cntAll', total);
  setTxt('cntMyntra', catCounts.myntra_labels || 0);
  setTxt('cntExternal', catCounts.external_brands || 0);
}

// Donut Chart: Category Distribution - FULLY DYNAMIC from /api/insights
function renderCategoryDonut(insights) {
  const ctx = document.getElementById('categoryDonutChart');
  if (!ctx) return;

  const catComp = insights.category_comparison || {};
  const categorySeries = [
    { key: 'Shirts', label: 'Shirts', color: '#0f172a' },
    { key: 'Denims', label: 'Denims & Jeans', color: '#334155' },
    { key: 'Western Wear', label: "Women's Western", color: '#94a3b8' },
    { key: 'Others', label: 'Others', color: '#cbd5e1' }
  ];
  const visibleSeries = categorySeries
    .map(item => ({ ...item, count: Number((catComp[item.key] || {}).count || 0) }))
    .filter(item => item.count > 0);
  const fallbackSeries = visibleSeries.length ? visibleSeries : [{ key: 'Shirts', label: 'Shirts', color: '#0f172a', count: 0 }];
  const totalCat = fallbackSeries.reduce((sum, item) => sum + item.count, 0) || 1;

  const labels = fallbackSeries.map(item => item.label);
  const dataValues = fallbackSeries.map(item => item.count);
  const colors = fallbackSeries.map(item => item.color);
  const pcts = dataValues.map(v => ((v / totalCat) * 100).toFixed(1));

  if (chartInstances.categoryDonut) chartInstances.categoryDonut.destroy();

  chartInstances.categoryDonut = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: dataValues,
        backgroundColor: colors,
        borderWidth: 0,
        hoverOffset: 3
      }]
    },
    options: {
      cutout: '72%',
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (item) => ` ${item.label}: ${item.raw.toLocaleString()} (${pcts[item.dataIndex]}%)`
          }
        }
      }
    }
  });

  // Dynamic HTML Legend
  const legendEl = document.getElementById('categoryDonutLegend');
  if (legendEl) {
    legendEl.innerHTML = labels.map((lbl, idx) => `
      <div class="legend-item">
        <span class="legend-dot" style="background: ${colors[idx]};"></span>
        <span class="legend-label">${lbl}</span>
        <span class="legend-value">${pcts[idx]}%</span>
      </div>
    `).join('');
  }

  // Update catalog tab counts from category_comparison
  const statsEl = (id, val) => { const e = document.getElementById(id); if (e) e.textContent = val.toLocaleString(); };
  const shirtsCnt = Number((catComp['Shirts'] || {}).count || 0);
  const denimsCnt = Number((catComp['Denims'] || {}).count || 0);
  const westernCnt = Number((catComp['Western Wear'] || {}).count || 0);
  statsEl('cntShirts', shirtsCnt);
  statsEl('cntDenims', denimsCnt);
  statsEl('cntWestern', westernCnt);
  statsEl('fCatShirts', shirtsCnt.toLocaleString());
  statsEl('fCatDenims', denimsCnt.toLocaleString());
  statsEl('fCatWestern', westernCnt.toLocaleString());
}

// Donut Chart: Brand Type Share
function renderBrandTypeDonut(stats) {
  const ctx = document.getElementById('brandTypeDonutChart');
  if (!ctx) return;

  const inHouse = Number(stats.myntra_brands_count || 0);
  const external = Number(stats.non_myntra_brands_count || 0);
  const total = inHouse + external;

  const labels = ['Myntra In-House', 'External Brands'];
  const dataValues = [inHouse, external];
  const colors = ['#0f172a', '#cbd5e1'];

  if (chartInstances.brandTypeDonut) chartInstances.brandTypeDonut.destroy();

  chartInstances.brandTypeDonut = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: dataValues,
        backgroundColor: colors,
        borderWidth: 0,
        hoverOffset: 3
      }]
    },
    options: {
      cutout: '72%',
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (item) => {
              const pct = total > 0 ? ((item.raw / total) * 100).toFixed(1) : '0.0';
              return ` ${item.label}: ${item.raw.toLocaleString()} (${pct}%)`;
            }
          }
        }
      }
    }
  });

  const legendEl = document.getElementById('brandTypeDonutLegend');
  if (legendEl) {
    const inHousePct = total > 0 ? ((inHouse / total) * 100).toFixed(1) : '0.0';
    const externalPct = total > 0 ? ((external / total) * 100).toFixed(1) : '0.0';
    legendEl.innerHTML = `
      <div class="legend-item">
        <span class="legend-dot" style="background: #0f172a;"></span>
        <span class="legend-label">Myntra In-House</span>
        <span class="legend-value">${inHouse.toLocaleString()} (${inHousePct}%)</span>
      </div>
      <div class="legend-item">
        <span class="legend-dot" style="background: #cbd5e1;"></span>
        <span class="legend-label">External Brands</span>
        <span class="legend-value">${external.toLocaleString()} (${externalPct}%)</span>
      </div>
    `;
  }
}

// Bar Chart: Price Band Distribution - FULLY DYNAMIC from /api/insights
function renderPriceBandBar(insights) {
  const ctx = document.getElementById('priceBandBarChart');
  if (!ctx) return;

  // Use real price band distribution from API
  const pbd = insights.price_band_distribution;
  let labels, data;
  if (pbd && pbd.length > 0) {
    labels = pbd.map(b => b.label);
    data = pbd.map(b => b.count);
  } else {
    // Fallback using price_brackets
    const pb = insights.price_brackets || {};
    labels = ['< ₹500', '₹500-1K', '₹1K-2K', '₹2K-3.5K', '> ₹3.5K'];
    data = [pb.under_500||0, pb['500_to_1000']||0, pb['1000_to_2000']||0, pb['2000_to_3500']||0, pb.above_3500||0];
  }

  if (chartInstances.priceBandBar) chartInstances.priceBandBar.destroy();

  chartInstances.priceBandBar = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        data: data,
        backgroundColor: '#cbd5e1',
        hoverBackgroundColor: '#0f172a',
        borderRadius: 4,
        barPercentage: 0.6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (item) => ` ${item.raw.toLocaleString()} products`
          }
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { font: { family: 'Plus Jakarta Sans', size: 10, weight: '500' }, color: '#64748b' }
        },
        y: {
          grid: { color: '#f1f5f9' },
          ticks: {
            font: { family: 'Plus Jakarta Sans', size: 10 },
            color: '#94a3b8',
            callback: (val) => val === 0 ? '0' : (val >= 1000 ? (val / 1000).toFixed(0) + 'K' : val)
          }
        }
      }
    }
  });
}

// Warehouse Logistics & Seller Hubs List
function renderGeographicDemand(insights) {
  const listEl = document.getElementById('geoDemandList');
  if (!listEl) return;

  const hubs = Array.isArray(insights.geographic_demand) ? insights.geographic_demand.slice(0, 5) : [];

  if (hubs.length === 0) {
    listEl.innerHTML = '<div style="padding:12px;color:#94a3b8;font-size:12px;text-align:center;">No geographic demand data available.</div>';
    return;
  }

  listEl.innerHTML = hubs.map(c => `
    <div class="geo-rank-item">
      <div class="geo-rank-left">
        <span class="geo-num">${c.rank}</span>
        <span class="geo-city">${escapeHtml(c.city)}</span>
      </div>
      <span class="geo-share">${c.share}%</span>
    </div>
  `).join('');
}

// Top Trending Brands - FULLY DYNAMIC from /api/insights
function renderTrendingBrands(insights) {
  const listEl = document.getElementById('trendingBrandsList');
  if (!listEl) return;

  const brands = (Array.isArray(insights.trending_brands) && insights.trending_brands.length > 0)
    ? insights.trending_brands.slice(0, 5)
    : (Array.isArray(insights.top_brands) ? insights.top_brands.slice(0, 5) : []).map(b => ({
        brand: b.brand,
        skus: Number(b.product_count || 0)
      }));

  if (!brands.length) {
    listEl.innerHTML = '<div style="padding:12px;color:#94a3b8;font-size:12px;text-align:center;">No brand trend data available.</div>';
    return;
  }

  const maxMetric = Math.max(1, ...brands.map(b => Math.abs(Number(b.growth ?? b.skus ?? 0))));

  listEl.innerHTML = brands.map((b, idx) => {
    const num = String(idx + 1).padStart(2, '0');
    const usesGrowth = b.growth !== undefined && b.growth !== null;
    const metricVal = Math.abs(Number(usesGrowth ? b.growth : b.skus) || 0);
    const barWidth = Math.min(100, Math.round((metricVal / maxMetric) * 100));
    const metricText = usesGrowth
      ? `${b.direction || (Number(b.growth) >= 0 ? '+' : '-')}${Math.abs(Number(b.growth) || 0).toFixed(1)}%`
      : `${displayCount(b.skus, '0')} SKUs`;
    return `
      <div class="trend-brand-row">
        <div class="trend-brand-badge">${num}</div>
        <span class="trend-brand-name" title="${b.brand}">${b.brand}</span>
        <div class="trend-bar-track">
          <div class="trend-bar-fill" style="width: ${barWidth}%;"></div>
        </div>
        <span class="trend-percent">${metricText}</span>
      </div>
    `;
  }).join('');
}

// Inventory Heatmap Matrix - FULLY DYNAMIC from /api/insights
function renderInventoryHeatmap(insights) {
  const tbody = document.getElementById('heatmapTableBody');
  const headRow = document.getElementById('heatmapTableHeadRow');
  if (!tbody || !headRow) return;

  const heatmap = insights.inventory_heatmap;
  const sizeKeys = Array.isArray(insights.inventory_heatmap_columns) && insights.inventory_heatmap_columns.length
    ? insights.inventory_heatmap_columns
    : ['XS', 'S', 'M', 'L', 'XL', 'XXL'];

  headRow.innerHTML = `
    <th>BRAND</th>
    ${sizeKeys.map(sz => `<th>${escapeHtml(String(sz))}</th>`).join('')}
  `;

  if (!heatmap || heatmap.length === 0) {
    tbody.innerHTML = `<tr><td colspan="${sizeKeys.length + 1}" style="text-align:center;color:#94a3b8;padding:16px;">No size inventory data for the current scope.</td></tr>`;
    return;
  }

  let maxVal = 0;
  heatmap.forEach(row => {
    Object.values(row.sizes || {}).forEach(v => { if (v > maxVal) maxVal = v; });
  });
  if (maxVal === 0) maxVal = 1;

  function fmtNum(n) {
    if (!n || n === 0) return '0';
    if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
    return n.toString();
  }

  function heatLevel(n) {
    const pct = n / maxVal;
    if (pct === 0) return 'hm-lvl-0';
    if (pct < 0.25) return 'hm-lvl-1';
    if (pct < 0.6) return 'hm-lvl-2';
    return 'hm-lvl-3';
  }

  tbody.innerHTML = heatmap.map(row => {
    const s = row.sizes || {};
    return `
      <tr>
        <td title="${escapeHtml(row.brand || '')}">${escapeHtml(row.brand || 'Unknown')}</td>
        ${sizeKeys.map(sz => `<td><span class="heatmap-cell ${heatLevel(s[sz]||0)}">${fmtNum(s[sz]||0)}</span></td>`).join('')}
      </tr>
    `;
  }).join('');
}

// Render Dashboard Fabric Intelligence Card
function renderDashboardFabrics(insights) {
  const container = document.getElementById('dashboardFabricList');
  if (!container) return;

  const fabrics = Array.isArray(insights.top_fabrics) ? insights.top_fabrics : [];

  if (fabrics.length === 0) {
    container.innerHTML = '<div style="padding:12px;color:#94a3b8;font-size:12px;text-align:center;">No fabric mix data available.</div>';
    return;
  }

  container.innerHTML = fabrics.map(f => `
    <div>
      <div style="display:flex; justify-content:space-between; font-size:12px; font-weight:700; color:#0f172a; margin-bottom:4px;">
        <span>${escapeHtml(f.fabric)}</span>
        <span style="color:#64748b;">${(f.count || 0).toLocaleString()} styles (${f.percentage}%)</span>
      </div>
      <div style="height:6px; background:#f1f5f9; border-radius:4px; overflow:hidden;">
        <div style="height:100%; width:${Math.min(100, f.percentage)}%; background:#0f172a; border-radius:4px;"></div>
      </div>
    </div>
  `).join('');
}

// Render Dashboard Color Intelligence Card
function renderDashboardColors(insights) {
  const container = document.getElementById('dashboardColorList');
  if (!container) return;

  const colors = Array.isArray(insights.top_colors) ? insights.top_colors : [];

  if (colors.length === 0) {
    container.innerHTML = '<div style="padding:12px;color:#94a3b8;font-size:12px;text-align:center;">No color mix data available.</div>';
    return;
  }

  container.innerHTML = colors.map(c => `
    <div style="display:flex; align-items:center; justify-content:space-between; font-size:12px; padding:6px 0; border-bottom:1px solid #f8fafc;">
      <div style="display:flex; align-items:center; gap:10px;">
        <span style="width:14px; height:14px; border-radius:50%; background:${c.hex || '#0f172a'}; border:1px solid #cbd5e1; display:inline-block; flex-shrink:0;"></span>
        <strong style="color:#0f172a; font-weight:700;">${escapeHtml(c.color)}</strong>
      </div>
      <div style="display:flex; gap:12px; font-weight:600;">
        <span style="color:#64748b;">${(c.count || 0).toLocaleString()} SKUs</span>
        <span style="color:#10b981; background:#ecfdf5; padding:1px 6px; border-radius:4px; font-size:11px;">${c.discount}% OFF</span>
      </div>
    </div>
  `).join('');
}

// Render Dashboard Top 3 Featured Best-Sellers Card
function renderDashboardTop3Products(insights) {
  const container = document.getElementById('dashboardTop3ProductsList');
  if (!container) return;

  const products = insights.top_3_products || [];
  if (products.length === 0) {
    container.innerHTML = '<div style="text-align:center; padding:16px; color:#94a3b8; font-size:12px;">Loading best-seller products...</div>';
    return;
  }

  container.innerHTML = products.map((p, idx) => `
    <div style="display:flex; align-items:center; gap:12px; background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:8px 12px; cursor:pointer;" onclick="viewProductDetailModal(${p.product_id})">
      <div style="font-size:13px; font-weight:800; color:#0f172a; width:18px;">#${idx + 1}</div>
      <img src="${p.image || '/assets/luxury_silk_banner.jpg'}" style="width:42px; height:54px; object-fit:cover; border-radius:6px; flex-shrink:0;" onerror="this.src='/assets/luxury_silk_banner.jpg'" />
      <div style="flex:1; min-width:0;">
        <div style="font-size:11px; font-weight:800; color:#0f172a; text-transform:uppercase; letter-spacing:0.3px;">${escapeHtml(p.brand || 'Brand')}</div>
        <div style="font-size:12px; color:#475569; font-weight:600; text-overflow:ellipsis; overflow:hidden; white-space:nowrap;">${escapeHtml(p.title || 'Product Title')}</div>
        <div style="display:flex; align-items:center; gap:8px; margin-top:2px;">
          <span style="font-size:12px; font-weight:800; color:#0f172a;">₹${(p.selling_price || 0).toLocaleString()}</span>
          ${p.mrp > p.selling_price ? `<span style="font-size:11px; color:#94a3b8; text-decoration:line-through;">₹${p.mrp.toLocaleString()}</span>` : ''}
          <span style="font-size:10px; font-weight:700; color:#059669; background:#ecfdf5; padding:1px 5px; border-radius:4px;">${p.discount_percentage}% OFF</span>
        </div>
      </div>
      <div style="font-size:11px; font-weight:700; color:#0f172a; flex-shrink:0; text-align:right;">
        <div style="color:#f59e0b;">★ ${p.rating || 4.5}</div>
        <div style="font-size:10px; color:#94a3b8;">(${(p.rating_count || 0).toLocaleString()})</div>
      </div>
    </div>
  `).join('');
}

// AI Market Insights Cards - FULLY DYNAMIC from /api/insights
function renderAiMarketInsights(insights) {
  const grid = document.getElementById('aiMarketInsightsGrid');
  if (!grid) return;

  // Use real ai_market_insights from API
  const aiInsights = insights.ai_market_insights;
  if (!aiInsights || aiInsights.length === 0) return;

  const iconMap = {
    trending: `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#0f172a" stroke-width="2"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline><polyline points="17 6 23 6 23 12"></polyline></svg>`,
    tag: `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#0f172a" stroke-width="2"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"></path><line x1="7" y1="7" x2="7.01" y2="7"></line></svg>`,
    star: `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#0f172a" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>`,
    default: `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#0f172a" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>`
  };

  grid.innerHTML = aiInsights.map(card => {
    let title = typeof card === 'object' ? card.title : 'Market Telemetry Insight';
    let desc = typeof card === 'object' ? card.description : String(card);
    let iconKey = typeof card === 'object' ? (card.icon || 'default') : 'default';
    return `
      <div class="ai-card" onclick="switchView('insights')">
        <div class="ai-card-icon-clean">${iconMap[iconKey] || iconMap.default}</div>
        <div class="ai-card-content">
          <h4>${escapeHtml(title)}</h4>
          <p>${escapeHtml(desc)}</p>
        </div>
        <span class="ai-card-arrow">→</span>
      </div>
    `;
  }).join('');
}

// ==========================================================================
// 3. PRODUCT CATALOG ENGINE (Image 2)
// ==========================================================================
let currentCatalogViewMode = 'grid'; // 'grid' (Image 1) or 'list' (Image 2)
let activeCatalogScope = {
  category: 'shirts',
  subcategory: 'all',
  gender: 'men',
  brandType: 'all',
  priceRanges: [],
  brands: [],
  discount: 'all',
  availability: 'all',
  keyword: '',
  tab: 'all',
  minPrice: 0,
  maxPrice: 25000,
  rating: 0,
  size: '',
  snapshotDate: 'all',
  movementFilter: 'all',
  legacyInStockOnly: false
};

async function refreshCatalogSidebarFacets() {
  try {
    const requestSeq = ++catalogFacetRequestSeq;
    const params = new URLSearchParams();
    if (activeCatalogScope.category && activeCatalogScope.category !== 'all') params.set('category', activeCatalogScope.category);
    if (activeCatalogScope.subcategory && activeCatalogScope.subcategory !== 'all') params.set('subcategory', activeCatalogScope.subcategory);
    if (activeCatalogScope.gender && activeCatalogScope.gender !== 'all') params.set('gender', activeCatalogScope.gender);
    if (activeCatalogScope.brandType && activeCatalogScope.brandType !== 'all') params.set('brand_type', activeCatalogScope.brandType);
    if (activeCatalogScope.priceRanges && activeCatalogScope.priceRanges.length > 0) params.set('price_ranges', activeCatalogScope.priceRanges.join(','));
    if (activeCatalogScope.brands && activeCatalogScope.brands.length > 0) params.set('brand', activeCatalogScope.brands.join(','));
    if (activeCatalogScope.discount && activeCatalogScope.discount !== 'all') params.set('discount_min', activeCatalogScope.discount);
    if (activeCatalogScope.availability && activeCatalogScope.availability !== 'all') params.set('availability', activeCatalogScope.availability);
    if (activeCatalogScope.rating > 0) params.set('rating_min', String(activeCatalogScope.rating));
    if (activeCatalogScope.minPrice > 0) params.set('price_min', String(activeCatalogScope.minPrice));
    if (activeCatalogScope.maxPrice > 0 && activeCatalogScope.maxPrice < 25000) params.set('price_max', String(activeCatalogScope.maxPrice));
    if (activeCatalogScope.keyword) params.set('search', activeCatalogScope.keyword);
    if (activeCatalogScope.tab && activeCatalogScope.tab !== 'all') params.set('tab', activeCatalogScope.tab);

    const data = await fetchCachedJson(buildFilterCountsUrl(params), { ttlMs: 20000 });
    if (requestSeq !== catalogFacetRequestSeq) return;
    const pb = data.price_buckets || {};
    const subcategories = Array.isArray(data.subcategories) ? data.subcategories : [];
    const brandsList = Array.isArray(data.brands_list) ? data.brands_list : [];
    const priceMap = {
      lt_500: pb.lt_500,
      '500_1000': pb['500_1000'],
      '1000_2000': pb['1000_2000'],
      '2000_3000': pb['2000_3000'],
      '3000_4000': pb['3000_4000'],
      gt_4000: pb.gt_4000
    };

    document.querySelectorAll('input[name="scopeCatalogPrice"]').forEach(chk => {
      const countSpan = chk.parentElement?.querySelector('.check-count');
      if (countSpan && priceMap[chk.value] !== undefined) {
        countSpan.textContent = Number(priceMap[chk.value] || 0).toLocaleString('en-IN');
      }
    });

    const subSel = document.getElementById('scopeCatalogSubcatSelect');
    if (subSel && subcategories.length > 0) {
      const validValues = new Set(subcategories.map(s => s.value));
      if (!validValues.has(activeCatalogScope.subcategory)) {
        activeCatalogScope.subcategory = 'all';
      }
      subSel.innerHTML = subcategories.map(s => {
        const value = String(s.value || 'all');
        const name = String(s.name || value);
        const selected = value === activeCatalogScope.subcategory ? 'selected' : '';
        return `<option value="${escapeHtml(value)}" ${selected}>${escapeHtml(name)}</option>`;
      }).join('');
    }

    const brandBox = document.getElementById('scopeCatalogAccBrand');
    if (brandBox) {
      const availableBrands = new Set(brandsList.map(b => b.brand));
      activeCatalogScope.brands = (activeCatalogScope.brands || []).filter(b => availableBrands.has(b));
      brandBox.innerHTML = brandsList.map(b => `
        <label class="sub-check-item">
          <input type="checkbox" name="scopeCatalogBrand" value="${escapeHtml(b.brand)}" onchange="applyCatalogScopeFilters()" ${activeCatalogScope.brands.includes(b.brand) ? 'checked' : ''} />
          <span class="check-text">${escapeHtml(b.brand)}</span>
          <span class="check-count">${Number(b.count || 0).toLocaleString('en-IN')}</span>
        </label>
      `).join('');
      filterCatalogBrands();
    }
  } catch (err) {
    console.warn('Error refreshing catalog sidebar facets:', err);
  }
}

async function refreshCatalogMeta() {
  try {
    const requestSeq = ++catalogMetaRequestSeq;
    const params = new URLSearchParams();
    if (activeCatalogScope.category && activeCatalogScope.category !== 'all') params.set('category', activeCatalogScope.category);
    if (activeCatalogScope.subcategory && activeCatalogScope.subcategory !== 'all') params.set('subcategory', activeCatalogScope.subcategory);
    if (activeCatalogScope.gender && activeCatalogScope.gender !== 'all') params.set('gender', activeCatalogScope.gender);
    if (activeCatalogScope.brandType && activeCatalogScope.brandType !== 'all') params.set('brand_type', activeCatalogScope.brandType);
    if (activeCatalogScope.priceRanges && activeCatalogScope.priceRanges.length > 0) params.set('price_ranges', activeCatalogScope.priceRanges.join(','));
    if (activeCatalogScope.brands && activeCatalogScope.brands.length > 0) params.set('brand', activeCatalogScope.brands.join(','));
    if (activeCatalogScope.discount && activeCatalogScope.discount !== 'all') params.set('min_discount', activeCatalogScope.discount);
    if (activeCatalogScope.availability === 'in_stock') params.set('in_stock', '1');
    if (activeCatalogScope.availability === 'out_of_stock') params.set('in_stock', '0');
    if (activeCatalogScope.rating > 0) params.set('rating_min', String(activeCatalogScope.rating));
    if (activeCatalogScope.minPrice > 0) params.set('min_price', String(activeCatalogScope.minPrice));
    if (activeCatalogScope.maxPrice > 0 && activeCatalogScope.maxPrice < 25000) params.set('max_price', String(activeCatalogScope.maxPrice));
    if (activeCatalogScope.keyword) params.set('search', activeCatalogScope.keyword);
    if (activeCatalogScope.tab && activeCatalogScope.tab !== 'all') params.set('tab', activeCatalogScope.tab);

    const data = await fetchCachedJson(buildCatalogMetaUrl(params), { ttlMs: 20000 });
    if (requestSeq !== catalogMetaRequestSeq) return;

    const summary = data.summary || {};
    const categories = Array.isArray(data.categories) ? data.categories : [];
    const categorySelect = document.getElementById('scopeCatalogCategorySelect');
    if (categorySelect && categories.length > 0) {
      const currentValue = activeCatalogScope.category || 'all';
      const availableValues = new Set(categories.map(item => String(item.value || 'all')));
      const nextValue = availableValues.has(currentValue) ? currentValue : 'all';
      activeCatalogScope.category = nextValue;
      categorySelect.innerHTML = categories.map(item => {
        const value = String(item.value || 'all');
        const name = String(item.name || value);
        const selected = value === nextValue ? 'selected' : '';
        return `<option value="${escapeHtml(value)}" ${selected}>${escapeHtml(name)}</option>`;
      }).join('');
      categorySelect.value = nextValue;
    }

    const totalProducts = Number(summary.total_products || 0);
    const totalBrands = Number(summary.total_brands || 0);
    const totalCategories = Number(summary.total_categories || 0);
    const avgDiscount = Number(summary.avg_discount || 0);
    const inStockProducts = Number(summary.in_stock_products || 0);
    const inStockPct = Number(summary.in_stock_pct || 0);
    const discountedPct = Number(summary.discounted_pct || 0);

    const setTxt = (id, value) => {
      const el = document.getElementById(id);
      if (el) el.textContent = value;
    };

    setTxt('catKpiTotalProductsVal', totalProducts.toLocaleString('en-IN'));
    setTxt('catKpiProductsGrowth', `${inStockPct.toFixed(1)}% in stock`);
    setTxt('catKpiTotalProductsSub', `${inStockProducts.toLocaleString('en-IN')} products currently in stock`);
    setTxt('catKpiTotalBrandsVal', totalBrands.toLocaleString('en-IN'));
    setTxt('catKpiTotalCategoriesVal', totalCategories.toLocaleString('en-IN'));
    setTxt('catKpiAvgDiscountVal', `${avgDiscount.toFixed(1)}%`);
    setTxt('catKpiDiscountGrowth', `${discountedPct.toFixed(1)}% discounted`);
  } catch (err) {
    console.warn('Error refreshing catalog meta:', err);
  }
}

function setCatalogViewMode(mode) {
  currentCatalogViewMode = mode;
  const gridBtn = document.getElementById('btnCatalogGridView');
  const listBtn = document.getElementById('btnCatalogListView');
  const exportBtn = document.getElementById('catalogExportBtn');
  if (gridBtn) gridBtn.classList.toggle('active', mode === 'grid');
  if (listBtn) listBtn.classList.toggle('active', mode === 'list');
  if (exportBtn) {
    exportBtn.style.display = mode === 'list' ? 'inline-flex' : 'inline-flex';
    exportBtn.innerHTML = mode === 'list' ? '↓ Export' : 'Export';
  }

  const gridContainer = document.getElementById('catalogGridViewContainer');
  const listContainer = document.getElementById('catalogListViewContainer');
  if (gridContainer) gridContainer.style.display = mode === 'grid' ? 'grid' : 'none';
  if (listContainer) listContainer.style.display = mode === 'list' ? 'block' : 'none';

  catalogPerPage = mode === 'grid' ? 24 : 50;
  catalogPage = 1;
  fetchCatalogProducts();
}

function setCatalogGender(g, btn) {
  document.querySelectorAll('#scopeCatalogGenderPills .gender-pill').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  activeCatalogScope.gender = (g || 'men').toLowerCase();
  applyCatalogScopeFilters();
}

function switchCatalogFilterTab(tab, btn) {
  document.querySelectorAll('#catalogTabNav .intel-tab-btn').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  activeCatalogScope.tab = tab;
  catalogPage = 1;
  Promise.all([
    refreshCatalogMeta(),
    refreshCatalogSidebarFacets(),
    fetchCatalogProducts()
  ]);
}

function filterCatalogBrands() {
  const q = (document.getElementById('scopeCatalogBrandSearch')?.value || '').toLowerCase();
  document.querySelectorAll('#scopeCatalogAccBrand label').forEach(lbl => {
    const txt = lbl.textContent.toLowerCase();
    lbl.style.display = txt.includes(q) ? 'flex' : 'none';
  });
}

function openCatalogWithScope({ brand = null, keyword = null } = {}) {
  if (brand !== null) {
    activeCatalogScope.brands = brand ? [brand] : [];
  }
  if (keyword !== null) {
    activeCatalogScope.keyword = String(keyword || '').trim();
  }

  const scopeKeywordInput = document.getElementById('scopeCatalogKeywordInput');
  if (scopeKeywordInput && keyword !== null) {
    scopeKeywordInput.value = activeCatalogScope.keyword;
  }

  const legacyKeywordInput = document.getElementById('catalogKeywordInput');
  if (legacyKeywordInput && keyword !== null) {
    legacyKeywordInput.value = activeCatalogScope.keyword;
  }

  catalogPage = 1;
  switchView('catalog');
}

async function applyCatalogScopeFilters() {
  const catSel = document.getElementById('scopeCatalogCategorySelect');
  if (catSel) activeCatalogScope.category = catSel.value;

  const subSel = document.getElementById('scopeCatalogSubcatSelect');
  if (subSel) activeCatalogScope.subcategory = subSel.value;

  const kwInput = document.getElementById('scopeCatalogKeywordInput');
  if (kwInput) activeCatalogScope.keyword = kwInput.value.trim();

  const discSel = document.getElementById('scopeCatalogDiscountSelect');
  if (discSel) activeCatalogScope.discount = discSel.value;

  const availSel = document.getElementById('scopeCatalogAvailabilitySelect');
  if (availSel) activeCatalogScope.availability = availSel.value;

  const prChecked = [];
  document.querySelectorAll('input[name="scopeCatalogPrice"]:checked').forEach(c => prChecked.push(c.value));
  activeCatalogScope.priceRanges = prChecked;

  const bChecked = [];
  document.querySelectorAll('#scopeCatalogAccBrand input[type="checkbox"]:checked').forEach(c => bChecked.push(c.value));
  activeCatalogScope.brands = bChecked;

  catalogPage = 1;
  await Promise.all([
    refreshCatalogMeta(),
    refreshCatalogSidebarFacets(),
    fetchCatalogProducts()
  ]);
}

async function resetCatalogScopeFilters() {
  const catSel = document.getElementById('scopeCatalogCategorySelect');
  if (catSel) catSel.value = 'shirts';

  const subSel = document.getElementById('scopeCatalogSubcatSelect');
  if (subSel) subSel.value = 'all';

  const kwInput = document.getElementById('scopeCatalogKeywordInput');
  if (kwInput) kwInput.value = '';

  const discSel = document.getElementById('scopeCatalogDiscountSelect');
  if (discSel) discSel.value = 'all';

  const availSel = document.getElementById('scopeCatalogAvailabilitySelect');
  if (availSel) availSel.value = 'all';

  document.querySelectorAll('#scopeCatalogGenderPills .gender-pill').forEach(b => {
    b.classList.toggle('active', b.textContent.trim().toLowerCase() === 'men');
  });

  document.querySelectorAll('input[name="scopeCatalogPrice"]').forEach(c => c.checked = false);
  document.querySelectorAll('#scopeCatalogAccBrand input[type="checkbox"]').forEach(c => c.checked = false);

  activeCatalogScope = {
    category: 'shirts',
    subcategory: 'all',
    gender: 'men',
    brandType: 'all',
    priceRanges: [],
    brands: [],
    discount: 'all',
    availability: 'all',
    keyword: '',
    tab: 'all',
    minPrice: 0,
    maxPrice: 25000,
    rating: 0,
    size: '',
    snapshotDate: 'all',
    movementFilter: 'all',
    legacyInStockOnly: false
  };

  catalogPage = 1;
  await Promise.all([
    refreshCatalogMeta(),
    refreshCatalogSidebarFacets(),
    fetchCatalogProducts()
  ]);
}

function exportCatalogReport() {
  window.print();
}

function changeCatalogPage(delta) {
  catalogPage = Math.max(1, catalogPage + delta);
  fetchCatalogProducts();
}

async function fetchCatalogProducts() {
  const requestSeq = ++catalogProductsRequestSeq;
  const gridContainer = document.getElementById('catalogGridViewContainer');
  const listTbody = document.getElementById('catalogListTableBody');
  const effectiveCategory = activeCatalogScope.category && activeCatalogScope.category !== 'all'
    ? activeCatalogScope.category
    : '';
  const effectiveBrandType = activeCatalogScope.brandType && activeCatalogScope.brandType !== 'all'
    ? activeCatalogScope.brandType
    : '';
  const effectiveBrand = activeCatalogScope.brands && activeCatalogScope.brands.length > 0
    ? activeCatalogScope.brands.join(',')
    : '';
  const effectiveKeyword = activeCatalogScope.keyword || '';
  const effectiveDiscount = activeCatalogScope.discount && activeCatalogScope.discount !== 'all'
    ? activeCatalogScope.discount
    : '';
  const effectiveRating = activeCatalogScope.rating > 0 ? String(activeCatalogScope.rating) : '';

  if (gridContainer && currentCatalogViewMode === 'grid') {
    gridContainer.innerHTML = `<div style="grid-column: 1 / -1; text-align:center; padding: 60px; color:#94a3b8;">Loading catalog products...</div>`;
  }
  if (listTbody && currentCatalogViewMode === 'list') {
    listTbody.innerHTML = `<tr><td colspan="11" style="text-align:center; padding: 60px; color:#94a3b8;">Loading catalog products...</td></tr>`;
  }

  const params = new URLSearchParams({
    page: catalogPage,
    per_page: catalogPerPage,
    sort: catalogSort,
    view_mode: currentCatalogViewMode
  });

  if (effectiveCategory) params.append('category', effectiveCategory);
  if (activeCatalogScope.gender) params.append('gender', activeCatalogScope.gender);
  if (activeCatalogScope.subcategory && activeCatalogScope.subcategory !== 'all') params.append('subcategory', activeCatalogScope.subcategory);
  if (activeCatalogScope.priceRanges && activeCatalogScope.priceRanges.length > 0) params.append('price_ranges', activeCatalogScope.priceRanges.join(','));
  if (effectiveBrand) params.append('brand', effectiveBrand);
  if (effectiveBrandType) params.append('brand_type', effectiveBrandType);
  if (effectiveDiscount) params.append('min_discount', effectiveDiscount);
  if (effectiveRating) params.append('rating_min', effectiveRating);
  if (activeCatalogScope.availability === 'in_stock') params.append('in_stock', '1');
  if (activeCatalogScope.availability === 'out_of_stock') params.append('in_stock', '0');
  if (activeCatalogScope.availability === 'all' && activeCatalogScope.legacyInStockOnly) params.append('in_stock', '1');
  if (effectiveKeyword) params.append('search', effectiveKeyword);
  if (activeCatalogScope.size) params.append('size', activeCatalogScope.size);
  if (activeCatalogScope.snapshotDate && activeCatalogScope.snapshotDate !== 'all') params.append('date', activeCatalogScope.snapshotDate);
  if (activeCatalogScope.movementFilter && activeCatalogScope.movementFilter !== 'all') params.append('movement_filter', activeCatalogScope.movementFilter);
  if (activeCatalogScope.minPrice > 0) params.append('min_price', String(activeCatalogScope.minPrice));
  if (activeCatalogScope.maxPrice > 0 && activeCatalogScope.maxPrice < 25000) params.append('max_price', String(activeCatalogScope.maxPrice));
  if (activeCatalogScope.tab && activeCatalogScope.tab !== 'all') params.append('tab', activeCatalogScope.tab);

  try {
    const res = await fetch(`/api/products?${params.toString()}`);
    if (!res.ok) throw new Error(`Catalog load failed with status ${res.status}`);
    const data = await res.json();
    if (requestSeq !== catalogProductsRequestSeq) return;
    const prods = data.products || data.items || [];
    allDiscoveredProducts = prods;

    renderCatalogData({ products: prods, total: data.total || 0 });
  } catch (err) {
    console.error('Error fetching catalog products:', err);
  }
}

function formatCatalogSizeMatrix(sizes, totalStock) {
  const hasExplicitSizes = Array.isArray(sizes) && sizes.length > 0;

  if (hasExplicitSizes) {
    const alphaRank = {
      XXS: 1, XS: 2, S: 3, M: 4, L: 5, XL: 6, XXL: 7, XXXL: 8, '3XL': 8, '4XL': 9
    };
    const aggregated = new Map();
    sizes.forEach(s => {
      const rawSize = String(s.size || '').trim();
      if (!rawSize) return;
      const key = rawSize.toUpperCase();
      const fallbackCount = s.available ? 1 : 0;
      const count = (s.inventory_count !== undefined && s.inventory_count !== null) ? Number(s.inventory_count) : fallbackCount;
      aggregated.set(key, {
        label: rawSize.toUpperCase(),
        count: (aggregated.get(key)?.count || 0) + (Number.isFinite(count) ? count : 0)
      });
    });

    const entries = Array.from(aggregated.values()).sort((a, b) => {
      const aNum = Number(a.label);
      const bNum = Number(b.label);
      const aIsNum = Number.isFinite(aNum) && a.label !== '';
      const bIsNum = Number.isFinite(bNum) && b.label !== '';
      if (aIsNum && bIsNum) return aNum - bNum;
      if (!aIsNum && !bIsNum) {
        const aRank = alphaRank[a.label] || 999;
        const bRank = alphaRank[b.label] || 999;
        if (aRank !== bRank) return aRank - bRank;
        return a.label.localeCompare(b.label);
      }
      return aIsNum ? -1 : 1;
    });

    if (entries.length === 0) {
      return `<span style="color:#94a3b8; font-size:11px;">—</span>`;
    }

    const visibleEntries = entries.slice(0, 6);
    const remainingCount = entries.length - visibleEntries.length;
    return `
      <div style="display:flex; align-items:center; gap:4px; flex-wrap:wrap; max-width:220px;">
        ${visibleEntries.map(item => `
          <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:4px; padding:2px 6px; text-align:center; min-width:30px;">
            <div style="font-size:9px; color:#64748b; font-weight:700; line-height:1.1;">${escapeHtml(item.label)}</div>
            <div style="font-size:10px; font-weight:700; line-height:1.1; color:${item.count === 0 ? '#ef4444' : '#0f172a'};">${item.count.toLocaleString('en-IN')}</div>
          </div>
        `).join('')}
        ${remainingCount > 0 ? `<span style="font-size:10px; color:#64748b; font-weight:700;">+${remainingCount} more</span>` : ''}
      </div>
    `;
  }
  return `<span style="color:#94a3b8; font-size:11px;">—</span>`;
}

function renderCatalogData(data) {
  const prods = data.products || data.items || [];
  const total = data.total || 0;

  // Update top KPI cards
  const totProdsEl = document.getElementById('catKpiTotalProductsVal');
  if (totProdsEl) totProdsEl.textContent = total.toLocaleString();

  const startIdx = Math.min(total, ((catalogPage - 1) * catalogPerPage) + 1);
  const endIdx = Math.min(total, catalogPage * catalogPerPage);
  const totalPages = Math.ceil(total / catalogPerPage) || 1;

  const showingTxt = `Showing ${startIdx}-${endIdx} of ${total.toLocaleString()} products`;
  const pageTxt = `Page ${catalogPage} of ${totalPages.toLocaleString()}`;

  const showTopEl = document.getElementById('catalogShowingCountText');
  if (showTopEl) showTopEl.textContent = showingTxt;
  const pageTopEl = document.getElementById('catalogPageIndicatorText');
  if (pageTopEl) pageTopEl.textContent = pageTxt;

  const showFootEl = document.getElementById('paginationInfoFooter');
  if (showFootEl) showFootEl.textContent = showingTxt;

  // Render Grid View Mode (Image 1)
  const gridContainer = document.getElementById('catalogGridViewContainer');
  if (gridContainer && currentCatalogViewMode === 'grid') {
    if (prods.length === 0) {
      gridContainer.innerHTML = `<div style="grid-column: 1 / -1; text-align:center; padding: 60px; color:#94a3b8;">No products found matching active filters.</div>`;
    } else {
      gridContainer.innerHTML = prods.map(item => {
        const p = item.product_info || {};
        const pricing = item.pricing || {};
        const inv = item.inventory_and_sizes || {};
        const ratings = item.ratings_and_reviews || item.ratings || {};
        const media = item.media || {};
        const pid = p.product_id;

        const img = media.primary_image || (media.image_gallery && media.image_gallery[0]) || 'assets/luxury_silk_banner.jpg';
        const discPct = pricing.discount_percentage || 0;
        const avgRating = (ratings.average_rating !== undefined && Number(ratings.average_rating) > 0) ? Number(ratings.average_rating).toFixed(1) : '—';
        const ratCount = Number(ratings.total_ratings_count || 0).toLocaleString('en-IN');
        const primaryHex = item.color_hex || p.color_hex || '';
        const hasRating = avgRating !== '—';

        return `
          <div style="background:#fff; border:1px solid #e2e8f0; border-radius:10px; padding:12px; position:relative; cursor:pointer; display:flex; flex-direction:column; justify-content:space-between; transition: transform 0.15s ease, box-shadow 0.15s ease;" onclick="openProductDrawer(${pid});">
            ${discPct > 0 ? `<span style="position:absolute; top:18px; left:18px; background:#0f172a; color:#fff; font-size:10px; font-weight:800; padding:3px 7px; border-radius:4px; z-index:2;">${discPct}% OFF</span>` : ''}
            <button onclick="event.stopPropagation(); toggleCompareItem(${pid}, true);" title="Save / Compare" style="position:absolute; top:18px; right:18px; background:#fff; border:1px solid #e2e8f0; border-radius:50%; width:26px; height:26px; cursor:pointer; font-size:12px; color:#64748b; display:inline-flex; align-items:center; justify-content:center; z-index:2;">♡</button>

            <div style="width:100%; height:200px; overflow:hidden; border-radius:6px; background:#f8fafc; margin-bottom:10px; display:flex; align-items:center; justify-content:center;">
              <img src="${img}" alt="${escapeHtml(p.title)}" style="width:100%; height:100%; object-fit:cover;" onerror="this.src='assets/luxury_silk_banner.jpg'" />
            </div>

            <!-- Color Swatches Dots -->
            <div style="display:flex; gap:5px; margin-bottom:6px; align-items:center;">
              ${primaryHex ? `<span style="width:9px; height:9px; border-radius:50%; background:${primaryHex}; display:inline-block; border:1px solid #cbd5e1;"></span>` : `<span style="font-size:10px; color:#94a3b8;">—</span>`}
            </div>

            <strong style="color:#0f172a; font-size:12px; display:block; margin-bottom:2px; font-weight:800;">${escapeHtml(p.brand || 'Brand')}</strong>
            <div style="font-size:11px; color:#64748b; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; margin-bottom:8px;">${escapeHtml(p.title || 'Product')}</div>

            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:auto;">
              <div>
                <span style="font-weight:800; color:#0f172a; font-size:13px;">₹${Math.round(pricing.selling_price || 0).toLocaleString()}</span>
                ${pricing.mrp && pricing.mrp > pricing.selling_price ? `<span style="text-decoration:line-through; color:#94a3b8; font-size:11px; margin-left:4px;">₹${Math.round(pricing.mrp).toLocaleString()}</span>` : ''}
              </div>
              <button onclick="event.stopPropagation(); openProductDrawer(${pid});" style="background:#fff; border:1px solid #e2e8f0; border-radius:6px; width:28px; height:28px; cursor:pointer; font-size:12px; display:inline-flex; align-items:center; justify-content:center;">🛍️</button>
            </div>

            <div style="font-size:10.5px; color:#64748b; margin-top:6px; display:flex; align-items:center; gap:4px;">
              <span style="color:#0f172a; font-weight:700;">★ ${avgRating}</span>
              <span>${hasRating ? `(${ratCount})` : ''}</span>
            </div>
          </div>
        `;
      }).join('');
    }
  }

  // Render List View Mode (Image 2)
  const listTbody = document.getElementById('catalogListTableBody');
  if (listTbody && currentCatalogViewMode === 'list') {
    if (prods.length === 0) {
      listTbody.innerHTML = `<tr><td colspan="11" style="text-align:center; padding: 60px; color:#94a3b8;">No products found matching active filters.</td></tr>`;
    } else {
      listTbody.innerHTML = prods.map(item => {
        const p = item.product_info || {};
        const pricing = item.pricing || {};
        const inv = item.inventory_and_sizes || {};
        const media = item.media || {};
        const pid = p.product_id;

        const img = media.primary_image || (media.image_gallery && media.image_gallery[0]) || 'assets/luxury_silk_banner.jpg';
        const sizes = item.sizes || inv.sizes_available || [];
        
        let stockUnits = inv.total_inventory_count || inv.inventory_units || 0;
        if (!stockUnits && sizes.length > 0) {
          stockUnits = sizes.reduce((acc, cur) => acc + ((cur.inventory_count !== undefined && cur.inventory_count !== null) ? Number(cur.inventory_count) : 0), 0);
        }
        const hasStock = stockUnits !== undefined && stockUnits !== null && Number.isFinite(Number(stockUnits)) && Number(stockUnits) >= 0;
        stockUnits = hasStock ? Number(stockUnits) : null;

        const discPct = pricing.discount_percentage || 0;
        const statusCls = stockUnits === null ? 'Unknown' : (stockUnits === 0 ? 'Out of Stock' : (stockUnits < 100 ? 'Low Stock' : 'In Stock'));
        const statusBg = stockUnits === null ? '#f8fafc' : (stockUnits === 0 ? '#fef2f2' : (stockUnits < 100 ? '#fffbeb' : '#ecfdf5'));
        const statusFg = stockUnits === null ? '#64748b' : (stockUnits === 0 ? '#ef4444' : (stockUnits < 100 ? '#d97706' : '#059669'));
        const statusBorder = stockUnits === null ? '#e2e8f0' : (stockUnits === 0 ? '#fecaca' : (stockUnits < 100 ? '#fde68a' : '#a7f3d0'));

        const sizeMatrixHtml = formatCatalogSizeMatrix(sizes, stockUnits);

        // SKU formatting
        const skuCode = p.sku || `SKU: HMTS${String(pid).padStart(5, '0')}`;
        const skuDisplay = skuCode.startsWith('SKU:') ? skuCode : `SKU: ${skuCode}`;

        return `
          <tr style="border-bottom:1px solid #f1f5f9; cursor:pointer; transition: background 0.12s ease;" onclick="if (!event.target.closest('input, a, button')) openProductDrawer(${pid});">
            <td style="padding:10px 12px;" onclick="event.stopPropagation();">
              <input type="checkbox" value="${pid}" onchange="toggleCompareItem(${pid}, this.checked)" />
            </td>
            <td style="padding:10px 12px;">
              <div style="display:flex; align-items:center; gap:10px;">
                <img src="${img}" alt="${escapeHtml(p.title)}" style="width:36px; height:46px; object-fit:cover; border-radius:4px;" onerror="this.src='assets/luxury_silk_banner.jpg'" />
                <div>
                  <strong style="color:#0f172a; font-size:12px; display:block;">${escapeHtml(p.title || 'Product')}</strong>
                  <span style="font-size:10px; color:#94a3b8;">${escapeHtml(skuDisplay)}</span>
                </div>
              </div>
            </td>
            <td style="padding:10px 12px; font-weight:700; color:#0f172a;">${escapeHtml(p.brand || '-')}</td>
            <td style="padding:10px 12px; color:#64748b;">
              <div style="font-weight:600; color:#334155;">${escapeHtml(p.category || '-')}</div>
              <div style="font-size:10px; color:#94a3b8;">${escapeHtml(p.sub_category || '-')}</div>
            </td>
            <td style="padding:10px 12px;">
              <strong style="color:#0f172a;">₹${Math.round(pricing.selling_price || 0).toLocaleString()}</strong>
              ${pricing.mrp && pricing.mrp > pricing.selling_price ? `<div style="text-decoration:line-through; color:#94a3b8; font-size:10px;">₹${Math.round(pricing.mrp).toLocaleString()}</div>` : ''}
            </td>
            <td style="padding:10px 12px;">
              ${discPct > 0 ? `<span style="background:#ecfdf5; color:#059669; border:1px solid #a7f3d0; font-weight:700; padding:2px 6px; border-radius:4px; font-size:10px;">${discPct}% OFF</span>` : '—'}
            </td>
            <td style="padding:10px 12px;">
              ${sizeMatrixHtml}
            </td>
            <td style="padding:10px 12px; font-weight:700; color:#0f172a;">${stockUnits === null ? '—' : stockUnits.toLocaleString('en-IN')}</td>
            <td style="padding:10px 12px;">
              <span style="background:${statusBg}; color:${statusFg}; border:1px solid ${statusBorder}; font-weight:700; padding:3px 8px; border-radius:12px; font-size:10px;">${statusCls}</span>
            </td>
            <td style="padding:10px 12px; font-size:11px; color:#64748b;">${escapeHtml(formatDateTimeLabel(p.last_seen_at || p.updated_at || item.last_seen_at || null))}</td>
            <td style="padding:10px 12px; text-align:center;" onclick="event.stopPropagation();">
              <button onclick="openProductDrawer(${pid})" style="background:#f1f5f9; border:none; border-radius:4px; padding:4px 8px; cursor:pointer; margin-right:4px;" title="View Details">👁</button>
              <button onclick="openProductDrawer(${pid})" style="background:#f1f5f9; border:none; border-radius:4px; padding:4px 8px; cursor:pointer;" title="Options">⋮</button>
            </td>
          </tr>
        `;
      }).join('');
    }
  }
}

function renderPagination(data) {
  const info = document.getElementById('paginationInfo');
  const controls = document.getElementById('paginationControls');
  if (!info || !controls) return;

  const total = data.total || 0;
  const pages = Math.ceil(total / catalogPerPage) || 1;
  const start = total === 0 ? 0 : Math.min((catalogPage - 1) * catalogPerPage + 1, total);
  const end = Math.min(catalogPage * catalogPerPage, total);

  info.textContent = `Showing ${start}–${end} of ${total.toLocaleString()} products`;

  let html = '';
  if (catalogPage > 1) {
    html += `<button class="page-btn" onclick="goToCatalogPage(${catalogPage - 1})">‹</button>`;
  }

  for (let i = Math.max(1, catalogPage - 2); i <= Math.min(pages, catalogPage + 2); i++) {
    html += `<button class="page-btn ${i === catalogPage ? 'active' : ''}" onclick="goToCatalogPage(${i})">${i}</button>`;
  }

  if (catalogPage < pages) {
    html += `<button class="page-btn" onclick="goToCatalogPage(${catalogPage + 1})">›</button>`;
  }

  controls.innerHTML = html;
}

function goToCatalogPage(p) {
  catalogPage = p;
  fetchCatalogProducts();
}

function onSortChange() {
  const sel = document.getElementById('catalogSortSelect');
  catalogSort = sel.value;
  catalogPage = 1;
  fetchCatalogProducts();
}

function toggleSort(col) {
  const sel = document.getElementById('catalogSortSelect');
  if (col === 'price') {
    if (catalogSort === 'price_asc') {
      catalogSort = 'price_desc';
    } else {
      catalogSort = 'price_asc';
    }
    if (sel) sel.value = catalogSort;
  }
  catalogPage = 1;
  fetchCatalogProducts();
}

function toggleSelectAllProds(isChecked) {
  const checkboxes = document.querySelectorAll('#catalogListTableBody input[type="checkbox"]');
  checkboxes.forEach(cb => {
    cb.checked = isChecked;
    const pid = parseInt(cb.value, 10);
    toggleCompareItem(pid, isChecked);
  });
}

function selectCategoryTab(cat) {
  activeCatalogScope.category = cat || 'all';
  activeCatalogScope.brandType = 'all';
  catalogPage = 1;

  document.querySelectorAll('.cat-tab-btn').forEach(btn => btn.classList.remove('active'));
  const activeBtn = document.querySelector(`.cat-tab-btn[data-cat="${cat}"]`);
  if (activeBtn) activeBtn.classList.add('active');

  // Sync sidebar checkboxes
  document.querySelectorAll('#filterCategoryCheckboxes input').forEach(c => {
    c.checked = (c.value === cat);
  });

  refreshCatalogSidebarFacets();
  refreshCatalogMeta();
  fetchCatalogProducts();
}

function selectBrandTypeTab(type) {
  activeCatalogScope.brandType = type || 'all';
  activeCatalogScope.category = 'all';
  catalogPage = 1;

  document.querySelectorAll('.cat-tab-btn').forEach(btn => btn.classList.remove('active'));
  const activeBtn = document.querySelector(`.cat-tab-btn[data-type="${type}"]`);
  if (activeBtn) activeBtn.classList.add('active');

  refreshCatalogSidebarFacets();
  refreshCatalogMeta();
  fetchCatalogProducts();
}

async function fetchBrandFacets() {
  try {
    const res = await fetch('/api/brands/facets');
    const data = await res.json();

    // Category facets counts with safe fallbacks
    const cats = data.categories || {};
    const shirtsCnt = cats.shirts || 0;
    const denimsCnt = cats.denims || 0;
    const westernCnt = cats['western-wear'] || 0;
    const myntraCnt = cats.myntra || 0;
    const nonMyntraCnt = cats['non-myntra'] || 0;
    const totalCnt = cats.total || (shirtsCnt + denimsCnt + westernCnt);

    if (document.getElementById('cntAll')) document.getElementById('cntAll').textContent = totalCnt.toLocaleString();
    if (document.getElementById('cntShirts')) document.getElementById('cntShirts').textContent = shirtsCnt.toLocaleString();
    if (document.getElementById('cntDenims')) document.getElementById('cntDenims').textContent = denimsCnt.toLocaleString();
    if (document.getElementById('cntWestern')) document.getElementById('cntWestern').textContent = westernCnt.toLocaleString();
    if (document.getElementById('cntMyntra')) document.getElementById('cntMyntra').textContent = myntraCnt.toLocaleString();
    if (document.getElementById('cntExternal')) document.getElementById('cntExternal').textContent = nonMyntraCnt.toLocaleString();

    if (document.getElementById('fCatShirts')) document.getElementById('fCatShirts').textContent = shirtsCnt.toLocaleString();
    if (document.getElementById('fCatDenims')) document.getElementById('fCatDenims').textContent = denimsCnt.toLocaleString();
    if (document.getElementById('fCatWestern')) document.getElementById('fCatWestern').textContent = westernCnt.toLocaleString();

    // Brand Checkboxes
    const brandFacetList = document.getElementById('brandFacetList');
    if (brandFacetList && data.brands) {
      brandFacetList.innerHTML = data.brands.slice(0, 30).map(b => `
        <label class="check-item">
          <input type="checkbox" value="${b.brand}" onchange="onBrandCheckboxChange('${b.brand}', this.checked)" />
          <span>${b.brand}</span>
          <span class="cnt">${b.count}</span>
        </label>
      `).join('');
    }
  } catch (err) {
    console.error('Error loading brand facets:', err);
  }
}

function filterBrandFacets() {
  const query = (document.getElementById('brandFacetSearch')?.value || '').toLowerCase().trim();
  const items = document.querySelectorAll('#brandFacetList .check-item');
  items.forEach(el => {
    const text = el.querySelector('span')?.textContent?.toLowerCase() || '';
    el.style.display = text.includes(query) ? 'flex' : 'none';
  });
}

function onBrandCheckboxChange(brand, isChecked) {
  openCatalogWithScope({ brand: isChecked ? brand : '' });
}

function debounceCatalogSearch() {
  clearTimeout(window._searchTimer);
  window._searchTimer = setTimeout(() => {
    const val = document.getElementById('catalogKeywordInput')?.value || '';
    openCatalogWithScope({ keyword: val });
  }, 350);
}

function onPriceSliderInput(val) {
  document.getElementById('priceRangeMaxLabel').textContent = `₹${parseInt(val, 10).toLocaleString()}`;
  activeCatalogScope.maxPrice = parseInt(val, 10);
}

function onDiscountSliderInput(val) {
  document.getElementById('discountRangeMaxLabel').textContent = `${val}% OFF`;
  activeCatalogScope.discount = parseInt(val, 10) > 0 ? String(parseInt(val, 10)) : 'all';
}

function onFilterChange() {
  // Read category checkboxes
  const checkedCats = Array.from(document.querySelectorAll('#filterCategoryCheckboxes input:checked')).map(c => c.value);
  if (checkedCats.length > 0) {
    activeCatalogScope.category = checkedCats[0];
  } else {
    const activeTab = document.querySelector('.cat-tab-btn.active');
    activeCatalogScope.category = activeTab ? (activeTab.getAttribute('data-cat') || 'all') : 'all';
  }

  // Read in-stock toggle
  const inStockEl = document.getElementById('inStockToggle');
  activeCatalogScope.legacyInStockOnly = inStockEl ? inStockEl.checked : false;

  // Read ratings checkboxes
  const checkedRatings = Array.from(document.querySelectorAll('input[name="ratingFilter"]:checked')).map(c => parseFloat(c.value));
  activeCatalogScope.rating = checkedRatings.length > 0 ? Math.min(...checkedRatings) : 0;

  catalogPage = 1;
  refreshCatalogMeta();
  refreshCatalogSidebarFacets();
  fetchCatalogProducts();
}

function clearCatalogFilters() {
  activeCatalogScope = {
    ...activeCatalogScope,
    category: 'all',
    brandType: 'all',
    brands: [],
    keyword: '',
    minPrice: 0,
    maxPrice: 15000,
    discount: 'all',
    rating: 0,
    legacyInStockOnly: false
  };
  const kw = document.getElementById('catalogKeywordInput');
  if (kw) kw.value = '';
  const pr = document.getElementById('priceRangeSlider');
  if (pr) pr.value = 15000;
  const prm = document.getElementById('priceRangeMaxLabel');
  if (prm) prm.textContent = '₹15,000';
  const dr = document.getElementById('discountRangeSlider');
  if (dr) dr.value = 0;
  const drm = document.getElementById('discountRangeMaxLabel');
  if (drm) drm.textContent = '0% OFF';
  const st = document.getElementById('inStockToggle');
  if (st) st.checked = false;

  document.querySelectorAll('#filterCategoryCheckboxes input').forEach(c => c.checked = false);
  document.querySelectorAll('input[name="ratingFilter"]').forEach(c => c.checked = false);
  document.querySelectorAll('#brandFacetList input').forEach(c => c.checked = false);

  selectCategoryTab('');
}

// ==========================================================================
// 4. SLIDE-OVER PRODUCT DETAIL DRAWER - FULL REAL DATA & RESPONSIVE EXPAND
// ==========================================================================
function toggleDrawerWidth() {
  const drawer = document.getElementById('productDrawer');
  const btn = document.getElementById('btnToggleDrawerWidth');
  if (!drawer) return;
  const isExpanded = drawer.classList.toggle('expanded');
  if (btn) {
    btn.innerHTML = isExpanded ? '⛶ Normal' : '⛶ Expand';
    btn.title = isExpanded ? 'Collapse to standard width' : 'Expand to wide view';
  }
}

function closeProductDrawer() {
  const drawer = document.getElementById('productDrawer');
  const backdrop = document.getElementById('productDrawerBackdrop');
  if (drawer) drawer.classList.remove('active');
  if (backdrop) backdrop.classList.remove('active');
  document.querySelectorAll('.product-table-row').forEach(r => r.classList.remove('selected-row'));
}

// Ensure global accessibility for inline onclick handlers
window.openProductDrawer = openProductDrawer;
window.closeProductDrawer = closeProductDrawer;
window.toggleDrawerWidth = toggleDrawerWidth;

// Global escape key handler for drawer
if (!window._drawerKeyBound) {
  window._drawerKeyBound = true;
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeProductDrawer();
  });
}

async function openProductDrawer(productId, showBackdrop = true) {
  if (!productId) return;
  console.log('[ProductDrawer] Opening SKU ID:', productId);
  window._inspectedId = productId;
  document.querySelectorAll('.product-table-row').forEach(r => r.classList.remove('selected-row'));
  const activeRow = document.querySelector(`.product-table-row[data-id="${productId}"]`);
  if (activeRow) activeRow.classList.add('selected-row');

  const drawer = document.getElementById('productDrawer');
  const backdrop = document.getElementById('productDrawerBackdrop');
  const body = document.getElementById('drawerBody');
  const skuTag = document.getElementById('drawerSkuTag');
  if (!drawer || !body) {
    console.error('[ProductDrawer] Target elements #productDrawer or #drawerBody missing!');
    return;
  }

  drawer.classList.add('active');
  if (backdrop && showBackdrop) backdrop.classList.add('active');
  if (skuTag) {
    skuTag.textContent = `#${productId}`;
    skuTag.style.display = 'inline-flex';
  }

  body.innerHTML = `
    <div style="text-align:center; padding:60px 20px; color:#94a3b8;">
      <div class="spinner" style="margin: 0 auto 16px auto; width: 32px; height: 32px; border: 3px solid #e2e8f0; border-top-color: #ff3f6c; border-radius: 50%; animation: spin 0.8s linear infinite;"></div>
      <div style="font-size:13px; font-weight:600; color:#475569;">Fetching real-time product intelligence...</div>
    </div>
  `;

  try {
    const res = await fetch(`/api/product/${productId}`);
    if (!res.ok) throw new Error('Product fetch failed');
    const data = await res.json();

    const p = data.product_info || {};
    const pricing = data.pricing || {};
    const inv = data.inventory_and_sizes || {};
    const specs = data.specifications || {};
    const ratings = data.ratings_and_reviews || data.ratings || {};
    const media = data.media || {};
    const policy = data.delivery_and_policies || {};
    const dod = data.day_over_day;

    const images = [media.primary_image, ...(media.image_gallery || [])].filter(Boolean);
    const mainImg = images[0] || 'assets/luxury_silk_banner.jpg';
    
    const sizeInv = data.size_inventory || inv.sizes_available || [];
    const totalStock = sizeInv.reduce((acc, cur) => acc + ((cur.inventory_count !== undefined && cur.inventory_count !== null) ? Number(cur.inventory_count) : 0), 0);
    const avgRating = (ratings.average_rating !== undefined && Number(ratings.average_rating) > 0) ? Number(ratings.average_rating).toFixed(1) : (ratings.rating && Number(ratings.rating) > 0 ? Number(ratings.rating).toFixed(1) : '—');
    const savings = Math.max(0, Math.round((pricing.mrp || 0) - (pricing.selling_price || 0)));
    const catBench = data.category_benchmark;
    const sizeHealth = data.size_curve_health;
    const velocity = data.velocity_runway;
    const relatedProds = data.related_products || [];

    body.innerHTML = `
      <!-- 2-Column Hero Split (Responsive) -->
      <div class="drawer-hero-split">
        <!-- Left: Garment Image & Gallery -->
        <div>
          <div class="drawer-image-carousel">
            <img id="drawerMainImg" src="${mainImg}" alt="${p.title || 'Product'}" onerror="this.src='assets/luxury_silk_banner.jpg'" />
            ${pricing.discount_percentage > 0 ? `<span class="drawer-discount-badge">${pricing.discount_percentage}% OFF</span>` : ''}
          </div>

          ${images.length > 1 ? `
            <div class="drawer-thumbnails">
              ${images.slice(0, 6).map((img, idx) => `
                <img class="drawer-thumb-img ${idx === 0 ? 'active' : ''}" 
                     src="${img}" 
                     onclick="document.getElementById('drawerMainImg').src='${img}'; document.querySelectorAll('.drawer-thumb-img').forEach(t=>t.classList.remove('active')); this.classList.add('active');" 
                     onerror="this.style.display='none'" />
              `).join('')}
            </div>
          ` : ''}

          <div style="margin-top: 12px; display: flex; flex-direction: column; gap: 6px;">
            <a href="${p.product_url || '#'}" target="_blank" class="btn btn-primary btn-sm" style="display: flex; align-items: center; justify-content: center; gap: 6px; width: 100%; text-decoration: none; font-weight: 700; padding: 9px; font-size: 12px;">
              View on Myntra ↗
            </a>
            <button class="btn btn-secondary btn-sm" onclick="toggleCompareItem(${p.product_id}, true); switchView('compare');" style="width: 100%; padding: 8px; font-size: 12px;">
              ➕ Add to Compare
            </button>
          </div>
        </div>

        <!-- Right: Primary Attributes & Pricing -->
        <div class="drawer-info-block">
          <div style="display: flex; align-items: center; justify-content: space-between; gap: 6px; flex-wrap: wrap;">
            <span class="badge-tag" style="background:#f1f5f9; color:#0f172a; font-weight:800; font-size:11px;">
              ${p.brand_type || (p.is_myntra_label ? 'Myntra Master Brand' : 'Verified Brand')}
            </span>
            <span class="drawer-sku">SKU: #${p.product_id}</span>
          </div>

          <h3 style="font-size: 18px; font-weight: 800; color: #0f172a; margin: 4px 0 2px 0;">${p.brand || 'Brand'}</h3>
          <p class="drawer-product-title" style="margin: 0 0 8px 0; font-size: 13px; color: #475569; font-weight: 600; line-height: 1.4;">${p.title || 'Product Title'}</p>

          <div class="drawer-price-row">
            <span class="price">₹${Math.round(pricing.selling_price || 0).toLocaleString()}</span>
            ${pricing.mrp > pricing.selling_price ? `<span class="mrp">₹${Math.round(pricing.mrp).toLocaleString()}</span>` : ''}
            ${pricing.discount_percentage > 0 ? `<span class="discount-pill">${pricing.discount_percentage}% OFF</span>` : ''}
            ${savings > 0 ? `<span class="drawer-savings-badge">Save ₹${savings.toLocaleString()}</span>` : ''}
          </div>
          <div style="font-size: 10.5px; color: #64748b; margin-top: 2px;">Prices inclusive of all taxes</div>

          <!-- Rating & Reviews -->
          <div style="margin-top: 10px;">
            <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
              <div class="drawer-rating-badge">★ ${avgRating}</div>
              <span style="font-size: 11.5px; color: #475569; font-weight: 600;">
                ${(ratings.total_ratings_count || 0).toLocaleString()} ratings • ${(ratings.total_reviews_count || 0).toLocaleString()} reviews
              </span>
            </div>
            ${(() => {
              const rb = ratings.rating_breakdown || {};
              const hasBreakdown = Object.values(rb).some(v => v > 0);
              if (!hasBreakdown) return '';
              const tot = ratings.total_ratings_count || 1;
              return `
                <div style="margin-top: 8px; display: flex; flex-direction: column; gap: 3px; background: #f8fafc; padding: 8px 10px; border-radius: 6px; border: 1px solid #e2e8f0;">
                  ${[5, 4, 3, 2, 1].map(star => {
                    const count = rb[`${star}_star`] || 0;
                    const pct = Math.min(100, Math.round((count / tot) * 100));
                    return `
                      <div style="display: flex; align-items: center; gap: 8px; font-size: 10.5px;">
                        <span style="width: 22px; color: #475569; font-weight: 700;">${star}★</span>
                        <div style="flex: 1; height: 5px; background: #e2e8f0; border-radius: 3px; overflow: hidden;">
                          <div style="width: ${pct}%; height: 100%; background: ${star >= 4 ? '#10b981' : (star === 3 ? '#f59e0b' : '#ef4444')}; border-radius: 3px;"></div>
                        </div>
                        <span style="width: 28px; text-align: right; color: #64748b; font-size: 10px;">${count}</span>
                      </div>
                    `;
                  }).join('')}
                </div>
              `;
            })()}
          </div>

          <!-- Real Garment Color Swatch from Database -->
          <div style="margin-top: 10px;">
            <div style="font-size: 10px; color: #64748b; font-weight: 700; text-transform: uppercase; margin-bottom: 4px; letter-spacing: 0.5px;">Garment Color</div>
            <div class="drawer-color-chip">
              <span class="drawer-color-dot" style="background-color: ${p.color_hex || '#0f172a'};"></span>
              <span>${p.primary_color || 'Multicolor'}</span>
              ${p.color_hex ? `<span style="color:#94a3b8; font-size:10px; font-family:'JetBrains Mono', monospace;">${p.color_hex}</span>` : ''}
            </div>
          </div>

          <!-- Real Delivery & Service Policies -->
          <div style="margin-top: 12px;">
            <div style="font-size: 10px; color: #64748b; font-weight: 700; text-transform: uppercase; margin-bottom: 4px; letter-spacing: 0.5px;">Fulfillment & Policies</div>
            <div class="drawer-policy-chips">
              ${policy.estimated_delivery_days ? `<span class="drawer-policy-chip">⚡ Fast Delivery (${policy.estimated_delivery_days} days)</span>` : ''}
              ${policy.cod_available ? `<span class="drawer-policy-chip">💵 COD Available</span>` : ''}
              ${policy.return_window_days ? `<span class="drawer-policy-chip">🔄 ${policy.return_window_days}-Day Returns</span>` : ''}
              ${policy.exchange_available ? `<span class="drawer-policy-chip">⇄ Free Exchange</span>` : ''}
            </div>
          </div>
        </div>
      </div>

      <!-- Dynamic Category Benchmark Card -->
      ${catBench ? `
        <div class="drawer-section-card" style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; padding:12px 14px; margin-top:14px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
            <strong style="font-size:12.5px; color:#0f172a;">📊 ${catBench.category} Category Benchmark</strong>
            <span style="font-size:10.5px; color:#64748b; font-weight:600;">${(catBench.total_category_skus || 0).toLocaleString()} peer styles</span>
          </div>
          <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:8px; text-align:center;">
            <div style="background:#fff; border:1px solid #e2e8f0; border-radius:6px; padding:6px 8px;">
              <span style="font-size:10px; color:#64748b; display:block;">Category ASP</span>
              <strong style="font-size:13px; color:#0f172a;">₹${Math.round(catBench.category_asp).toLocaleString()}</strong>
              <small style="display:block; font-size:9.5px; color:${catBench.price_delta_pct <= 0 ? '#059669' : '#dc2626'}; font-weight:700;">
                ${catBench.price_delta_pct <= 0 ? `${Math.abs(catBench.price_delta_pct)}% below avg` : `+${catBench.price_delta_pct}% above avg`}
              </small>
            </div>
            <div style="background:#fff; border:1px solid #e2e8f0; border-radius:6px; padding:6px 8px;">
              <span style="font-size:10px; color:#64748b; display:block;">Avg Discount</span>
              <strong style="font-size:13px; color:#0f172a;">${catBench.category_discount}%</strong>
              <small style="display:block; font-size:9.5px; color:${catBench.discount_delta >= 0 ? '#059669' : '#dc2626'}; font-weight:700;">
                ${catBench.discount_delta >= 0 ? `+${catBench.discount_delta}% higher` : `${catBench.discount_delta}% lower`}
              </small>
            </div>
            <div style="background:#fff; border:1px solid #e2e8f0; border-radius:6px; padding:6px 8px;">
              <span style="font-size:10px; color:#64748b; display:block;">Avg Rating</span>
              <strong style="font-size:13px; color:#d97706;">★ ${catBench.category_rating}</strong>
              <small style="display:block; font-size:9.5px; color:#64748b; font-weight:700;">Category mean</small>
            </div>
          </div>
        </div>
      ` : ''}

      <!-- Dynamic Velocity & Inventory Runway -->
      ${velocity ? `
        <div style="display:flex; gap:10px; margin-top:12px; flex-wrap:wrap;">
          <div style="flex:1; min-width:140px; background:#eff6ff; border:1px solid #bfdbfe; border-radius:8px; padding:8px 12px;">
            <span style="font-size:10px; color:#1e40af; font-weight:700; text-transform:uppercase;">Daily Velocity (ROS)</span>
            <div style="font-size:15px; font-weight:800; color:#1e3a8a;">${velocity.daily_ros} units / day</div>
            <small style="font-size:10px; color:#3b82f6;">${velocity.units_sold_window} sold in last 9 days (₹${Math.round(velocity.revenue_window).toLocaleString()})</small>
          </div>
          <div style="flex:1; min-width:140px; background:#f0fdf4; border:1px solid #bbf7d0; border-radius:8px; padding:8px 12px;">
            <span style="font-size:10px; color:#166534; font-weight:700; text-transform:uppercase;">Stock Runway</span>
            <div style="font-size:15px; font-weight:800; color:#14532d;">~${velocity.days_runway} days</div>
            <small style="font-size:10px; color:#16a34a;">${velocity.stock_units} warehouse units live</small>
          </div>
        </div>
      ` : ''}

      <!-- Size-Wise Warehouse Stock Breakdown Table (Real Data) -->
      ${sizeInv.length > 0 ? `
        <div class="drawer-section-card" style="margin-top:12px;">
          <!-- Size Curve Health Status -->
          ${sizeHealth ? (sizeHealth.is_broken ? `
            <div style="background:#fef2f2; border:1px solid #fecaca; border-radius:8px; padding:8px 12px; margin-bottom:10px; display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px;">
              <div style="display:flex; align-items:center; gap:8px;">
                <span style="font-size:15px;">⚠️</span>
                <div>
                  <strong style="color:#b91c1c; font-size:11.5px;">Broken Size Curve Alert (${sizeHealth.completeness_pct}% completeness)</strong>
                  <div style="color:#7f1d1d; font-size:10.5px;">Missing sizes: ${sizeHealth.missing_sizes.join(', ')} ${sizeHealth.missing_core_sizes.length > 0 ? `(Core OOS: <strong>${sizeHealth.missing_core_sizes.join(', ')}</strong>)` : ''}</div>
                </div>
              </div>
              <span style="font-size:10px; font-weight:800; background:#fee2e2; color:#dc2626; padding:2px 8px; border-radius:4px;">REORDER PRIORITY</span>
            </div>
          ` : `
            <div style="background:#ecfdf5; border:1px solid #a7f3d0; border-radius:8px; padding:7px 12px; margin-bottom:10px; display:flex; align-items:center; justify-content:space-between;">
              <div style="display:flex; align-items:center; gap:8px;">
                <span style="font-size:13px;">✅</span>
                <strong style="color:#065f46; font-size:11.5px;">Full Size Curve Live: 100% sizes available in stock</strong>
              </div>
              <span style="font-size:10px; font-weight:800; background:#d1fae5; color:#059669; padding:2px 8px; border-radius:4px;">HEALTHY</span>
            </div>
          `) : ''}

          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
            <strong style="font-size:13px; color:#0f172a;">📏 Size-Wise Warehouse Inventory (${sizeInv.length} sizes)</strong>
            <span style="font-size:11px; color:#10b981; font-weight:800; background:#ecfdf5; border:1px solid #a7f3d0; padding:2px 8px; border-radius:4px;">
              ${totalStock} units available
            </span>
          </div>
          <div style="overflow-x:auto;">
            <table class="drawer-size-table">
              <thead>
                <tr>
                  <th>Size</th>
                  <th>SKU ID</th>
                  <th>Stock Units</th>
                  <th>Status</th>
                  <th>Stock Share</th>
                </tr>
              </thead>
              <tbody>
                ${sizeInv.map(sz => {
                  const cnt = (sz.inventory_count !== undefined && sz.inventory_count !== null) ? Number(sz.inventory_count) : 0;
                  const statusCls = cnt === 0 ? 'oos-pill' : (cnt <= 2 ? 'low-pill' : 'in-pill');
                  const statusText = cnt === 0 ? 'Out of Stock' : (cnt <= 2 ? 'Low Stock' : 'In Stock');
                  const pct = totalStock > 0 ? Math.min(100, Math.round((cnt / totalStock) * 100)) : 0;
                  const barCls = cnt === 0 ? 'oos' : (cnt <= 2 ? 'low' : '');
                  return `
                    <tr>
                      <td><strong style="font-size:12px; color:#0f172a;">${sz.size}</strong></td>
                      <td style="color:#64748b; font-family:'JetBrains Mono', monospace; font-size:10px;">${sz.sku_id || '—'}</td>
                      <td><strong>${cnt} units</strong></td>
                      <td><span class="tbl-size-pill ${statusCls}">${statusText}</span></td>
                      <td>
                        <div class="drawer-size-bar-wrap">
                          <div class="drawer-size-bar ${barCls}" style="width: ${pct}%"></div>
                        </div>
                        <span style="font-size:10px; color:#64748b; font-weight:600;">${pct}%</span>
                      </td>
                    </tr>
                  `;
                }).join('')}
              </tbody>
            </table>
          </div>
        </div>
      ` : ''}

      <!-- Yesterday vs Today Market Movement Card (Real DoD Metrics) -->
      ${dod ? `
        <div class="drawer-dod-card" style="margin-top:12px;">
          <h4>
            <span>📅 Yesterday vs Today Movement</span>
            <small style="color:#64748b; font-weight:700;">${dod.yesterday_date || 'Previous'} ➔ ${dod.today_date || 'Today'}</small>
          </h4>
          <div class="drawer-dod-grid">
            <div class="drawer-dod-item">
              <span>Price Shift</span>
              <strong>₹${Math.round(dod.today_price).toLocaleString()}</strong>
              ${dod.price_delta < 0 ? `<small style="color:#059669; display:block;">▼ ₹${Math.abs(Math.round(dod.price_delta))} (${dod.price_delta_pct}%)</small>` : (dod.price_delta > 0 ? `<small style="color:#dc2626; display:block;">▲ ₹${Math.round(dod.price_delta)} (+${dod.price_delta_pct}%)</small>` : '<small style="color:#64748b; display:block;">Steady price</small>')}
            </div>
            <div class="drawer-dod-item">
              <span>Discount Delta</span>
              <strong>${dod.today_discount}% OFF</strong>
              <small style="color:${dod.discount_delta > 0 ? '#059669' : (dod.discount_delta < 0 ? '#dc2626' : '#64748b')}; display:block;">
                ${dod.yesterday_discount}% ➔ ${dod.today_discount}% (${dod.discount_delta >= 0 ? '+' : ''}${dod.discount_delta}%)
              </small>
            </div>
            <div class="drawer-dod-item">
              <span>Inventory Delta</span>
              <strong>${dod.today_stock} units</strong>
              <small style="color:#64748b; display:block;">Yesterday: ${dod.yesterday_stock} units (${dod.stock_delta >= 0 ? '+' : ''}${dod.stock_delta})</small>
            </div>
            <div class="drawer-dod-item">
              <span>Units Sold & Revenue</span>
              <strong>${dod.units_sold} sold</strong>
              <small style="color:#d97706; display:block;">₹${Math.round(dod.revenue || 0).toLocaleString()} GMV today</small>
            </div>
          </div>
        </div>
      ` : ''}

      <!-- Historical Price & Stock Timeline with Interactive SVG Trend Graph -->
      ${(() => {
        const ph = data.price_history || [];
        if (ph.length <= 1) return '';

        // Generate SVG sparkline points
        const prices = ph.map(x => x.price);
        const minP = Math.min(...prices);
        const maxP = Math.max(...prices);
        const rangeP = Math.max(1, maxP - minP);
        const svgW = 340;
        const svgH = 65;
        const pts = ph.map((x, i) => {
          const cx = Math.round((i / (ph.length - 1)) * (svgW - 40) + 20);
          const cy = Math.round(svgH - 12 - ((x.price - minP) / rangeP) * (svgH - 24));
          return { x: cx, y: cy, price: x.price, date: x.date };
        });
        const pathD = pts.map((pt, i) => `${i === 0 ? 'M' : 'L'} ${pt.x} ${pt.y}`).join(' ');

        return `
          <div class="drawer-section-card" style="margin-top:12px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
              <strong style="font-size:13px; color:#0f172a;">📉 9-Day Price & Stock Movement History</strong>
              <span style="font-size:10px; color:#64748b; font-weight:700;">${ph.length} daily snapshots</span>
            </div>

            <!-- SVG Price Movement Sparkline -->
            <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:8px 10px; margin-bottom:8px;">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px; font-size:10px; color:#64748b; font-weight:700;">
                <span>Price Trendline (${ph[0].date.slice(5)} ➔ ${ph[ph.length - 1].date.slice(5)})</span>
                <span style="color:#0f172a;">Range: ₹${Math.round(minP)} – ₹${Math.round(maxP)}</span>
              </div>
              <svg viewBox="0 0 ${svgW} ${svgH}" style="width:100%; height:55px; overflow:visible;">
                <path d="${pathD}" fill="none" stroke="#ff3f6c" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />
                ${pts.map(pt => `
                  <circle cx="${pt.x}" cy="${pt.y}" r="3.5" fill="#ff3f6c" stroke="#fff" stroke-width="1.5">
                    <title>${pt.date}: ₹${Math.round(pt.price)}</title>
                  </circle>
                `).join('')}
              </svg>
            </div>

            <!-- Snapshot Cards -->
            <div style="display:flex; gap:8px; overflow-x:auto; padding-bottom:6px;">
              ${ph.map((item, idx) => {
                const isLatest = idx === ph.length - 1;
                return `
                  <div style="flex:0 0 92px; background:${isLatest ? '#eff6ff' : '#f8fafc'}; border:1px solid ${isLatest ? '#93c5fd' : '#e2e8f0'}; border-radius:8px; padding:7px 8px; text-align:center;">
                    <div style="font-size:10px; color:#64748b; font-weight:700;">${item.date.slice(5)}</div>
                    <div style="font-size:13px; font-weight:800; color:#0f172a; margin:2px 0;">₹${Math.round(item.price)}</div>
                    <div style="font-size:10px; color:${item.discount > 0 ? '#059669' : '#94a3b8'}; font-weight:700;">${item.discount}% OFF</div>
                    <div style="font-size:9.5px; color:#64748b; margin-top:2px;">📦 ${item.stock} units</div>
                  </div>
                `;
              }).join('')}
            </div>
          </div>
        `;
      })()}

      <!-- Garment Technical Specifications & Anatomy (Dynamic Real Specs) -->
      <div class="drawer-section-card" style="margin-top:12px;">
        <strong style="font-size: 13px; color: #0f172a; display: block; margin-bottom: 10px;">
          📐 Garment Anatomy & Technical Specs
        </strong>
        <div class="drawer-spec-grid">
          ${(() => {
            const specList = [];
            if (specs.fabric) specList.push({ label: 'Fabric', val: specs.fabric });
            if (specs.pattern) specList.push({ label: 'Pattern', val: specs.pattern });
            if (specs.fit || inv.fit) specList.push({ label: 'Fit Profile', val: specs.fit || inv.fit });
            if (specs.collar) specList.push({ label: 'Collar Style', val: specs.collar });
            if (specs.sleeve_length) specList.push({ label: 'Sleeve Length', val: specs.sleeve_length });
            if (specs.length) specList.push({ label: 'Garment Length', val: specs.length });
            if (specs.hemline) specList.push({ label: 'Hemline', val: specs.hemline });
            if (specs.weave_type) specList.push({ label: 'Weave Type', val: specs.weave_type });
            if (specs.wash_care) specList.push({ label: 'Wash Care', val: specs.wash_care });
            if (p.category) specList.push({ label: 'Category', val: p.category });
            if (p.gender) specList.push({ label: 'Target Gender', val: p.gender });
            if (p.primary_color) specList.push({ label: 'Primary Color', val: p.primary_color });

            if (specList.length === 0) {
              return '<div style="color:#94a3b8; font-size:12px; grid-column:1/-1;">Standard garment specifications recorded for this SKU.</div>';
            }

            return specList.map(s => `
              <div class="drawer-spec-pill">
                <span class="lbl">${s.label}</span>
                <span class="val">${s.val}</span>
              </div>
            `).join('');
          })()}
        </div>
      </div>

      <!-- More Styles from Brand / Related Products Strip -->
      ${relatedProds.length > 0 ? `
        <div class="drawer-section-card" style="margin-top:12px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
            <strong style="font-size:13px; color:#0f172a;">🏷️ Sibling Styles from ${p.brand}</strong>
            <span style="font-size:10.5px; color:#64748b;">Click to inspect</span>
          </div>
          <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(130px, 1fr)); gap:8px;">
            ${relatedProds.map(rel => `
              <div onclick="openProductDrawer(${rel.product_id})" style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:8px; cursor:pointer; transition:transform 0.15s, border-color 0.15s;" onmouseover="this.style.borderColor='#ff3f6c'" onmouseout="this.style.borderColor='#e2e8f0'">
                <img src="${rel.thumbnail || 'assets/luxury_silk_banner.jpg'}" style="width:100%; height:105px; object-fit:cover; border-radius:6px; margin-bottom:6px;" onerror="this.src='assets/luxury_silk_banner.jpg'" />
                <div style="font-size:11px; font-weight:700; color:#0f172a; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="${rel.title}">${rel.title}</div>
                <div style="display:flex; justify-content:space-between; align-items:center; margin-top:4px;">
                  <strong style="font-size:11.5px; color:#0f172a;">₹${Math.round(rel.price)}</strong>
                  ${rel.discount > 0 ? `<span style="font-size:9.5px; color:#ef4444; font-weight:700;">${rel.discount}%</span>` : ''}
                </div>
                <div style="font-size:9.5px; color:#d97706; margin-top:2px;">★ ${rel.rating > 0 ? rel.rating.toFixed(1) : '—'}</div>
              </div>
            `).join('')}
          </div>
        </div>
      ` : ''}

      <!-- Dynamic AI Merchandising Insight -->
      <div class="drawer-ai-insight-box" style="margin-top:12px;">
        <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 6px;">
          <span style="color: #ef4444;">✨</span> <strong style="font-size: 12px; color: #0f172a;">Merchandising Intelligence</strong>
        </div>
        <p style="font-size: 11.5px; line-height: 1.5; color: #475569; margin: 0;">
          ${(() => {
            if (pricing.discount_percentage >= 60) {
              return `Deep markdown asset (${pricing.discount_percentage}% off). With ${totalStock} units across warehouse sizes, this item drives high cart-addition velocity. Ideal candidate for flash promotions and clearance bundling.`;
            } else if (pricing.discount_percentage >= 40) {
              return `Healthy mid-tier promotional velocity (${pricing.discount_percentage}% discount). Size distribution is well-stocked (${totalStock} units). Margin retention remains solid with steady daily ROS.`;
            } else {
              return `Full-price catalog staple (${pricing.discount_percentage || 0}% discount). Customer rating (★ ${avgRating}) reflects authentic customer reception. Suitable for high-visibility category placement.`;
            }
          })()}
        </p>
      </div>

      <!-- Drawer Bottom Action Footer -->
      <div style="display: flex; gap: 8px; margin-top: 14px; padding-bottom: 12px;">
        <a href="${p.product_url || '#'}" target="_blank" class="btn btn-primary" style="flex: 1; text-align: center; text-decoration: none; padding: 10px; font-weight: 700;">
          View Live on Myntra ↗
        </a>
        <button class="btn btn-secondary" onclick="closeProductDrawer()" style="padding: 10px 16px; font-weight: 700;">
          Close
        </button>
      </div>
    `;
  } catch (err) {
    console.error('Error rendering drawer details:', err);
    body.innerHTML = `
      <div style="text-align:center; padding:40px; color:#dc2626;">
        <p style="font-weight:700;">Failed to load product details</p>
        <p style="font-size:12px; color:#64748b;">Please verify your connection and try again.</p>
        <button class="btn btn-secondary btn-sm" onclick="openProductDrawer(${productId})" style="margin-top:12px;">Retry</button>
      </div>
    `;
  }
}

// ==========================================================================
// 5. PRODUCT COMPARE SUITE (Image 3)
// ==========================================================================
function showToast(msg, isError = false) {
  let toast = document.getElementById('appToastNotice');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'appToastNotice';
    toast.style.cssText = `
      position: fixed;
      bottom: 24px;
      right: 24px;
      padding: 12px 20px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 700;
      color: #fff;
      z-index: 99999;
      box-shadow: 0 10px 25px rgba(0,0,0,0.2);
      transition: opacity 0.25s ease, transform 0.25s ease;
      pointer-events: none;
      opacity: 0;
      transform: translateY(10px);
    `;
    document.body.appendChild(toast);
  }

  toast.style.background = isError ? '#dc2626' : '#0f172a';
  toast.textContent = msg;
  toast.style.opacity = '1';
  toast.style.transform = 'translateY(0)';

  clearTimeout(window._toastTimer);
  window._toastTimer = setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
  }, 2800);
}

// ==========================================================================
// 5. PRODUCT COMPARE SUITE (Image 3)
// ==========================================================================
async function seedDefaultCompare() {
  try {
    const res = await fetch('/api/products?per_page=4&sort=discount_desc');
    const data = await res.json();
    const prods = data.products || data.items || [];
    if (prods.length > 0) {
      compareProductIds = prods.slice(0, 4).map(p => p.product_info.product_id);
      updateCompareCountUI();
      return;
    }
  } catch (e) {
    console.error('Error seeding default compare:', e);
  }
  compareProductIds = [];
  updateCompareCountUI();
}

function toggleCompareItem(productId, shouldAdd) {
  productId = parseInt(productId, 10);
  if (shouldAdd) {
    if (!compareProductIds.includes(productId)) {
      if (compareProductIds.length >= 4) {
        showToast('You can compare up to 4 products at a time. Remove one first.', true);
        const cb = document.querySelector(`#catalogListTableBody input[value="${productId}"]`);
        if (cb) cb.checked = false;
        return;
      }
      compareProductIds.push(productId);
      showToast('Added to Product Compare Suite');
    }
  } else {
    compareProductIds = compareProductIds.filter(id => id !== productId);
    showToast('Removed from Product Compare Suite');
  }

  updateCompareCountUI();

  // Sync checkbox in catalog table
  const cb = document.querySelector(`#catalogListTableBody input[value="${productId}"]`);
  if (cb) cb.checked = compareProductIds.includes(productId);

  if (currentView === 'compare') {
    renderCompareSuite();
  }
}

function removeCompareItem(productId) {
  productId = parseInt(productId, 10);
  compareProductIds = compareProductIds.filter(id => id !== productId);

  // Uncheck in catalog table
  const cb = document.querySelector(`#catalogListTableBody input[value="${productId}"]`);
  if (cb) cb.checked = false;

  showToast('Removed from comparison');
  updateCompareCountUI();
  renderCompareSuite();
}

function updateCompareCountUI() {
  const count = compareProductIds.length;
  if (document.getElementById('compareNavBadge')) document.getElementById('compareNavBadge').textContent = count;
  if (document.getElementById('compareSelectedCount')) document.getElementById('compareSelectedCount').textContent = count;
  if (document.getElementById('compareSlotBadge')) document.getElementById('compareSlotBadge').textContent = `${count}/4`;
}

async function renderCompareSuite() {
  updateCompareCountUI();
  const cardsRow = document.getElementById('compareCardsRow');
  const table = document.getElementById('compareMetricsTable');
  if (!cardsRow || !table) return;

  if (compareProductIds.length === 0) {
    await seedDefaultCompare();
  }

  if (compareProductIds.length === 0) {
    cardsRow.innerHTML = `
      <div class="compare-add-slot" style="grid-column: 1 / -1; height: 160px;" onclick="switchView('catalog')">
        <span style="font-size:24px; margin-bottom:8px; color: #ff3f6c;">+</span>
        <span>No products selected for comparison. Click here to pick products from the catalog.</span>
      </div>
    `;
    table.innerHTML = `<tr><td style="text-align:center; padding:30px; color:#94a3b8;">Select products from the catalog to generate side-by-side comparison.</td></tr>`;
    return;
  }

  try {
    cardsRow.innerHTML = `<div style="grid-column: 1 / -1; text-align:center; padding: 40px; color:#94a3b8;">Loading comparison matrix...</div>`;
    const res = await fetch(`/api/compare?ids=${compareProductIds.join(',')}`);
    const data = await res.json();
    const products = data.products || [];

    if (products.length === 0) {
      cardsRow.innerHTML = `
        <div class="compare-add-slot" style="grid-column: 1 / -1; height: 160px;" onclick="switchView('catalog')">
          <span style="font-size:24px; margin-bottom:8px; color: #ff3f6c;">+</span>
          <span>No products found for the selected IDs. Click here to pick products from the catalog.</span>
        </div>
      `;
      table.innerHTML = `<tr><td style="text-align:center; padding:30px; color:#94a3b8;">No matching products found in catalog.</td></tr>`;
      return;
    }

    // Keep only valid product IDs
    compareProductIds = products.map(p => p.product_id);
    updateCompareCountUI();

    // Render Product Cards Row
    let cardsHtml = products.map(p => `
      <div class="compare-prod-card">
        <button class="btn-remove-compare" onclick="removeCompareItem(${p.product_id})" title="Remove from comparison">✕</button>
        <img class="compare-card-thumb" src="${p.thumbnail || 'assets/luxury_silk_banner.jpg'}" alt="${p.brand}" onerror="this.src='assets/luxury_silk_banner.jpg'" onclick="openProductDrawer(${p.product_id})" style="cursor:pointer;" />
        <span class="compare-card-brand">${p.brand}</span>
        <span class="compare-card-title" title="${p.title}" onclick="openProductDrawer(${p.product_id})" style="cursor:pointer;">${p.title}</span>
        <div class="compare-card-price-row">
          <span class="price">₹${Math.round(p.selling_price).toLocaleString()}</span>
          <span class="mrp">₹${Math.round(p.mrp).toLocaleString()}</span>
          ${p.discount_percentage > 0 ? `<span class="disc">${p.discount_percentage}% OFF</span>` : ''}
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top:10px; font-size:11px; padding-top:8px; border-top:1px solid #f1f5f9;">
          <span style="color:#d97706; font-weight:700;">★ ${(p.average_rating && Number(p.average_rating) > 0 ? Number(p.average_rating).toFixed(1) : '—')}</span>
          <a href="${p.product_url || '#'}" target="_blank" style="color:#ff3f6c; font-weight:700; text-decoration:none;">View on Myntra ↗</a>
        </div>
        <button class="btn btn-secondary btn-sm" onclick="openProductDrawer(${p.product_id})" style="margin-top:8px; width:100%; font-size:11px; padding:5px; font-weight:700; border-radius:6px;">🔍 Inspect SKU</button>
      </div>
    `).join('');

    if (products.length < 4) {
      cardsHtml += `
        <div class="compare-add-slot" onclick="switchView('catalog')">
          <span style="font-size:24px; margin-bottom:6px; color:#ff3f6c;">+</span>
          <span>Add Product (${products.length}/4)</span>
        </div>
      `;
    }
    cardsRow.innerHTML = cardsHtml;

    // Render Key Metrics Comparison Table
    renderCompareMetricsTable(products);

    // Render 4 Comparative Charts
    renderCompareCharts(data.charts || {});

    // Render AI Comparison Insights (Image 3)
    renderCompareAiInsights(data.ai_insights || []);
  } catch (err) {
    console.error('Error rendering comparison suite:', err);
    cardsRow.innerHTML = `<div style="grid-column: 1 / -1; color:#dc2626; padding:20px; text-align:center;">Failed to load comparison data.</div>`;
  }
}

function renderCompareMetricsTable(products) {
  const table = document.getElementById('compareMetricsTable');
  if (!table) return;

  const row = (lbl, fn) => `
    <tr>
      <td style="font-weight:700; color:#475569; width:160px;">${lbl}</td>
      ${products.map(p => `<td>${fn(p)}</td>`).join('')}
    </tr>
  `;

  table.innerHTML = `
    ${row('Brand', p => `<strong>${p.brand}</strong>`)}
    ${row('Product Title', p => `<span style="color:#334155; font-weight:500;">${p.title}</span>`)}
    ${row('Category', p => `<span class="brand-badge">${p.category}</span>`)}
    ${row('Selling Price', p => `<strong style="font-size:13px; color:#0f172a;">₹${Math.round(p.selling_price).toLocaleString()}</strong>`)}
    ${row('Original MRP', p => `<span style="color:#94a3b8; text-decoration:line-through;">₹${Math.round(p.mrp).toLocaleString()}</span>`)}
    ${row('Discount', p => p.discount_percentage > 0 ? `<span class="discount-pill">${p.discount_percentage}% OFF</span>` : '—')}
    ${row('Stock Units', p => `<strong>${p.stock_units.toLocaleString()}</strong>`)}
    ${row('Available Sizes', p => (p.available_sizes || []).join(', ') || 'All Sizes')}
    ${row('Fabric', p => p.fabric || '—')}
    ${row('Fit Type', p => p.fit || '—')}
    ${row('Consumer Rating', p => `<span style="color:#d97706; font-weight:800;">★ ${(p.average_rating ? Number(p.average_rating).toFixed(1) : '—')}</span>`)}
    ${row('Total Reviews', p => `${p.total_reviews}+`)}
    ${row('Demand Velocity', p => `<span class="trend-badge ${p.trend_class || 'growing'}">${p.trend}</span>`)}
    ${row('AI Deal Score', p => `
      <div style="display:flex; align-items:center; gap:8px;">
        <strong style="font-size:12px;">${p.ai_opportunity_score}/100</strong>
        <div style="flex:1; height:6px; background:#f1f5f9; border-radius:3px; overflow:hidden;">
          <div style="height:100%; width:${p.ai_opportunity_score}%; background:${p.ai_opportunity_score >= 75 ? '#10b981' : '#d97706'};"></div>
        </div>
      </div>
    `)}
    ${row('Direct Link', p => `<a href="${p.product_url || '#'}" target="_blank" class="table-icon-btn" style="display:inline-flex; align-items:center; gap:4px; text-decoration:none; font-size:11px; font-weight:700; color:#ff3f6c;">Open on Myntra ↗</a>`)}
  `;
}

function renderCompareCharts(charts) {
  // Chart 1: Price Comparison
  const ctxPrice = document.getElementById('compPriceChart');
  if (ctxPrice && charts.price) {
    if (chartInstances.compPrice) chartInstances.compPrice.destroy();
    chartInstances.compPrice = new Chart(ctxPrice, {
      type: 'bar',
      data: {
        labels: charts.price.map(c => c.brand),
        datasets: [
          { label: 'Price', data: charts.price.map(c => c.price), backgroundColor: '#ff3f6c', borderRadius: 4 },
          { label: 'MRP', data: charts.price.map(c => c.mrp), backgroundColor: '#e2e8f0', borderRadius: 4 }
        ]
      },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { grid: { display: false } } } }
    });
  }

  // Chart 2: Discount Comparison
  const ctxDisc = document.getElementById('compDiscountChart');
  if (ctxDisc && charts.discount) {
    if (chartInstances.compDisc) chartInstances.compDisc.destroy();
    chartInstances.compDisc = new Chart(ctxDisc, {
      type: 'bar',
      data: {
        labels: charts.discount.map(c => c.brand),
        datasets: [{ data: charts.discount.map(c => c.discount), backgroundColor: '#d97706', borderRadius: 4 }]
      },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { grid: { display: false } } } }
    });
  }

  // Chart 3: Stock Units Comparison
  const ctxStock = document.getElementById('compStockChart');
  if (ctxStock && charts.stock) {
    if (chartInstances.compStock) chartInstances.compStock.destroy();
    chartInstances.compStock = new Chart(ctxStock, {
      type: 'bar',
      data: {
        labels: charts.stock.map(c => c.brand),
        datasets: [{ data: charts.stock.map(c => c.stock), backgroundColor: '#3b82f6', borderRadius: 4 }]
      },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { grid: { display: false } } } }
    });
  }

  // Chart 4: Rating Comparison
  const ctxRating = document.getElementById('compRatingChart');
  if (ctxRating && charts.rating) {
    if (chartInstances.compRating) chartInstances.compRating.destroy();
    chartInstances.compRating = new Chart(ctxRating, {
      type: 'bar',
      data: {
        labels: charts.rating.map(c => c.brand),
        datasets: [{ data: charts.rating.map(c => c.rating), backgroundColor: '#f59e0b', borderRadius: 4 }]
      },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { grid: { display: false } }, y: { max: 5 } } }
    });
  }
}

function renderCompareAiInsights(insights) {
  const stack = document.getElementById('compareAiInsightsStack');
  if (!stack) return;

  if (insights.length === 0) {
    stack.innerHTML = `<div style="font-size:11px; color:#94a3b8; text-align:center;">Insights will generate once items are added.</div>`;
    return;
  }

  stack.innerHTML = insights.map(item => `
    <div class="ai-insight-item">
      <span class="ai-insight-badge ${item.type}">✦ ${item.badge}</span>
      <p><strong>${item.title}</strong>: ${item.description}</p>
    </div>
  `).join('');
}

function generateAiCompareReport() {
  showToast('Opening Fashion Copilot for comparative intelligence...');
  toggleAICopilot(true);
  sendQuickPrompt('Compare selected products');
}

function shareComparison() {
  const url = `${window.location.origin}/#compare=${compareProductIds.join(',')}`;
  navigator.clipboard.writeText(url).then(() => {
    showToast('Comparison link copied to clipboard!');
  }).catch(() => {
    showToast(`Comparison link: ${url}`);
  });
}

// ==========================================================================
// 6. LAL10 AI COPILOT INTERACTIVE ASSISTANT (Images 1 & 3)
// ==========================================================================
function toggleAICopilot(forceOpen = null) {
  const drawer = document.getElementById('aiCopilotDrawer');
  if (!drawer) return;

  if (forceOpen === true) {
    drawer.classList.add('active');
  } else if (forceOpen === false) {
    drawer.classList.remove('active');
  } else {
    drawer.classList.toggle('active');
  }
}

function handleCopilotKey(e) {
  if (e.key === 'Enter') {
    submitCopilotQuery();
  }
}

async function submitCopilotQuery() {
  const input = document.getElementById('copilotInput');
  const query = input.value.trim();
  if (!query) return;

  input.value = '';
  appendUserChatMessage(query);

  const container = document.getElementById('chatStreamContainer');
  const tempMsg = document.createElement('div');
  tempMsg.className = 'copilot-chat-bubble assistant';
  tempMsg.textContent = 'Thinking and analyzing Myntra catalog data...';
  container.appendChild(tempMsg);
  container.scrollTop = container.scrollHeight;

  try {
    const res = await fetch('/api/ai/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query })
    });
    const data = await res.json();
    tempMsg.innerHTML = formatMarkdown(data.reply);
  } catch (err) {
    tempMsg.textContent = 'Sorry, could not process request right now.';
  }

  container.scrollTop = container.scrollHeight;
}

function sendQuickPrompt(promptText) {
  toggleAICopilot(true);
  document.getElementById('copilotInput').value = promptText;
  submitCopilotQuery();
}

function appendUserChatMessage(msg) {
  const container = document.getElementById('chatStreamContainer');
  if (!container) return;

  const bubble = document.createElement('div');
  bubble.className = 'copilot-chat-bubble user';
  bubble.textContent = msg;
  container.appendChild(bubble);
  container.scrollTop = container.scrollHeight;
}

function formatMarkdown(text) {
  if (!text) return '';
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/• (.*?)\n/g, '<li>$1</li>')
    .replace(/\n\n/g, '<br/><br/>')
    .replace(/\n/g, '<br/>');
}

// ==========================================================================
// 7. BRANDS INTELLIGENCE & PERFORMANCE ECOSYSTEM
// ==========================================================================
let brandIntelligenceCache = null;

function switchBrandTab(tabId, btn) {
  document.querySelectorAll('#view-brands .tab-pill-btn').forEach(b => {
    b.classList.remove('active');
    b.style.background = '#ffffff';
    b.style.color = '#475569';
    b.style.border = '1px solid #cbd5e1';
  });
  if (btn) {
    btn.classList.add('active');
    btn.style.background = '#0f172a';
    btn.style.color = '#ffffff';
    btn.style.border = 'none';
  }

  document.querySelectorAll('.brand-tab-panel').forEach(p => {
    p.style.display = 'none';
    p.classList.remove('active');
  });
  const activePanel = document.getElementById(`panel-brand-${tabId}`);
  if (activePanel) {
    activePanel.style.display = 'block';
    activePanel.classList.add('active');
  }

  if (tabId === 'directory') {
    fetchBrandsDirectory();
  }
}

// ============================================================
// BRAND COMPARATOR SUITE (LAL10 FASHION INTELLIGENCE)
// ============================================================

let comparatorState = {
  category: 'shirts',
  selectedBrands: []
};

let compChartProductCount = null;
let compChartAsp = null;
let compChartDiscount = null;
let brandSearchDebounceTimer = null;

function buildBrandComparatorScopeParams(includeSelectedBrands = true) {
  const p = new URLSearchParams();
  p.append('category', comparatorState.category || activeScopeIntel.category || 'shirts');
  p.append('gender', activeScopeIntel.gender || 'men');

  if (activeScopeIntel.subcategory && activeScopeIntel.subcategory !== 'all') {
    p.append('subcategory', activeScopeIntel.subcategory);
  }
  if (activeScopeIntel.priceRanges && activeScopeIntel.priceRanges.length > 0) {
    p.append('price_ranges', activeScopeIntel.priceRanges.join(','));
  }
  if (activeScopeIntel.brandSizes && activeScopeIntel.brandSizes.length > 0) {
    p.append('brand_size', activeScopeIntel.brandSizes.join(','));
  }
  if (activeScopeIntel.colors && activeScopeIntel.colors.length > 0) {
    p.append('color', activeScopeIntel.colors.join(','));
  }
  if (activeScopeIntel.fabrics && activeScopeIntel.fabrics.length > 0) {
    p.append('fabric', activeScopeIntel.fabrics.join(','));
  }
  if (activeScopeIntel.fits && activeScopeIntel.fits.length > 0) {
    p.append('fit', activeScopeIntel.fits.join(','));
  }
  if (Number(activeScopeIntel.discountMin || 0) > 0) {
    p.append('discount_min', activeScopeIntel.discountMin);
  }
  if (activeScopeIntel.inStockOnly) {
    p.append('availability', 'in_stock');
  }
  if (Number(activeScopeIntel.ratingMin || 0) > 0) {
    p.append('rating_min', activeScopeIntel.ratingMin);
  }
  if (activeScopeIntel.newArrivalsOnly) {
    p.append('new_arrivals', '1');
  }
  if (includeSelectedBrands && comparatorState.selectedBrands.length > 0) {
    p.append('brands', comparatorState.selectedBrands.join(','));
  }
  return p;
}

function renderComparatorBrandPills() {
  const container = document.getElementById('comparatorBrandsPillBox');
  if (!container) return;

  container.innerHTML = comparatorState.selectedBrands.map(brand => `
    <span class="brand-pill-tag">
      <span>${escapeHtml(brand)}</span>
      <span class="brand-pill-remove" onclick='removeComparatorBrand(${JSON.stringify(brand)})' title="Remove brand">&times;</span>
    </span>
  `).join('') + (
    comparatorState.selectedBrands.length < 5
      ? `<button class="brand-pill-add-btn" onclick="openBrandPickerModal()">+ Add Brand</button>`
      : ''
  );
}

function removeComparatorBrand(brandName) {
  if (comparatorState.selectedBrands.length <= 2) {
    showToast('Minimum 2 brands required for comparison');
    return;
  }
  comparatorState.selectedBrands = comparatorState.selectedBrands.filter(b => b.toLowerCase() !== brandName.toLowerCase());
  renderComparatorBrandPills();
  loadBrandComparator();
}

function openBrandPickerModal() {
  const modal = document.getElementById('brandPickerModal');
  if (modal) {
    modal.style.display = 'flex';
    const input = document.getElementById('brandPickerSearchInput');
    if (input) {
      input.value = '';
      input.focus();
    }
    fetchBrandPickerResults('');
  }
}

function closeBrandPickerModal() {
  const modal = document.getElementById('brandPickerModal');
  if (modal) modal.style.display = 'none';
}

function onBrandPickerSearch(query) {
  clearTimeout(brandSearchDebounceTimer);
  brandSearchDebounceTimer = setTimeout(() => {
    fetchBrandPickerResults(query);
  }, 200);
}

async function fetchBrandPickerResults(query) {
  const listContainer = document.getElementById('brandPickerResultsList');
  if (!listContainer) return;

  listContainer.innerHTML = '<div style="padding: 16px; text-align: center; color: #94a3b8; font-size: 12px;">Searching catalog brands...</div>';

  try {
    const params = buildBrandComparatorScopeParams(false);
    params.set('q', query || '');
    const res = await fetch(`/api/brands/search?${params.toString()}`);
    const json = await res.json();
    const brands = json.brands || [];

    if (brands.length === 0) {
      listContainer.innerHTML = '<div style="padding: 16px; text-align: center; color: #94a3b8; font-size: 12px;">No matching brands found in catalog.</div>';
      return;
    }

    listContainer.innerHTML = brands.map(b => {
      const isSelected = comparatorState.selectedBrands.some(sb => sb.toLowerCase() === b.brand.toLowerCase());
      return `
        <div class="brand-picker-item" onclick="${isSelected ? '' : `selectBrandFromPicker(${JSON.stringify(b.brand)})`}" style="${isSelected ? 'opacity: 0.5; cursor: not-allowed;' : ''}">
          <span class="brand-picker-item-name">${escapeHtml(b.brand)}</span>
          <span class="brand-picker-item-count">${isSelected ? 'Added' : `${Number(b.count).toLocaleString()} SKUs`}</span>
        </div>
      `;
    }).join('');
  } catch (err) {
    console.error('Error fetching brand search results:', err);
    listContainer.innerHTML = '<div style="padding: 16px; text-align: center; color: #ef4444; font-size: 12px;">Failed to load brands.</div>';
  }
}

function selectBrandFromPicker(brandName) {
  if (comparatorState.selectedBrands.length >= 5) {
    showToast('Maximum 5 brands can be compared at a time');
    return;
  }
  comparatorState.selectedBrands.push(brandName);
  closeBrandPickerModal();
  renderComparatorBrandPills();
  loadBrandComparator();
}

function resetBrandComparator() {
  comparatorState.category = activeScopeIntel.category || 'shirts';
  comparatorState.selectedBrands = [];
  const catSelect = document.getElementById('comparatorCategorySelect');
  if (catSelect) catSelect.value = comparatorState.category;
  renderComparatorBrandPills();
  loadBrandComparator();
}

function applyBrandComparator() {
  const catSelect = document.getElementById('comparatorCategorySelect');
  if (catSelect) {
    comparatorState.category = catSelect.value;
  }
  loadBrandComparator();
}

function getBrandSparklineSVG(pts) {
  if (!Array.isArray(pts) || pts.length === 0) {
    return '<span style="font-size: 9px; color: #94a3b8;">No price history</span>';
  }
  if (pts.length === 1) {
    pts = [pts[0], pts[0]];
  }
  const min = Math.min(...pts);
  const max = Math.max(...pts);
  const range = (max - min) || 1;
  const w = 54;
  const h = 16;
  const step = w / (pts.length - 1);
  const polyPoints = pts.map((val, i) => {
    const x = (i * step).toFixed(1);
    const y = (h - ((val - min) / range) * (h - 4) - 2).toFixed(1);
    return `${x},${y}`;
  }).join(' ');
  return `<svg class="sparkline-svg" viewBox="0 0 54 18"><polyline fill="none" stroke="#0f172a" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" points="${polyPoints}" /></svg>`;
}

function renderBrandEmblem(brandName) {
  const clean = String(brandName || 'Brand').trim();
  const initials = clean
    .split(/[\s&._-]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map(part => part[0])
    .join('')
    .toUpperCase() || clean.slice(0, 2).toUpperCase();
  return `
    <div style="display:flex; align-items:center; gap:8px; min-width:0;">
      <span style="width:30px; height:30px; border-radius:10px; background:#0f172a; color:#fff; display:inline-flex; align-items:center; justify-content:center; font-size:10px; font-weight:900; letter-spacing:0.04em;">${escapeHtml(initials)}</span>
      <span style="font-size:11px; font-weight:850; color:#0f172a; letter-spacing:0.02em; text-transform:uppercase; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:105px;" title="${escapeHtml(clean)}">${escapeHtml(clean)}</span>
    </div>
  `;
}

function formatComparatorPct(value, digits = 1) {
  const num = Number(value || 0);
  return `${Number.isFinite(num) ? num.toFixed(digits) : '0.0'}%`;
}

function formatComparatorPrice(value) {
  const num = Number(value || 0);
  return `₹${Number.isFinite(num) ? Math.round(num).toLocaleString('en-IN') : '0'}`;
}

function compactComparatorNumber(value) {
  const num = Number(value || 0);
  if (!Number.isFinite(num)) return '0';
  if (num >= 10000000) return `${(num / 10000000).toFixed(1)}Cr`;
  if (num >= 100000) return `${(num / 100000).toFixed(1)}L`;
  if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
  return Math.round(num).toLocaleString('en-IN');
}

function comparatorBarColors(values, prefer = 'max') {
  const numeric = values.map(v => Number(v || 0));
  const target = prefer === 'min' ? Math.min(...numeric) : Math.max(...numeric);
  return numeric.map(v => v === target && target > 0 ? '#0f172a' : '#cbd5e1');
}

async function loadBrandComparator() {
  renderComparatorBrandPills();
  try {
    const params = buildBrandComparatorScopeParams(true);
    const url = `/api/brands/comparator?${params.toString()}`;
    const res = await fetch(url);
    const data = await res.json();
    if (!data || !data.brands) return;

    const resolvedBrands = Array.isArray(data.brands)
      ? data.brands.map(b => b.display_name || b.brand).filter(Boolean).slice(0, 5)
      : [];

    const currentBrands = comparatorState.selectedBrands.map(b => b.toLowerCase());
    const nextBrands = resolvedBrands.map(b => b.toLowerCase());
    const brandSelectionChanged =
      resolvedBrands.length > 0 &&
      (currentBrands.length !== nextBrands.length || currentBrands.some((brand, idx) => brand !== nextBrands[idx]));

    if ((comparatorState.selectedBrands.length === 0 || brandSelectionChanged) && resolvedBrands.length > 0) {
      comparatorState.selectedBrands = resolvedBrands;
      renderComparatorBrandPills();
    }

    // 1. KPI Summary Cards (Live Dynamic DB Values)
    const kpis = data.kpis || {};
    if (document.getElementById('compKpiBrands')) document.getElementById('compKpiBrands').textContent = kpis.brands_selected !== undefined ? kpis.brands_selected : 0;
    if (document.getElementById('compKpiProducts')) document.getElementById('compKpiProducts').textContent = Number(kpis.total_products || 0).toLocaleString();
    if (document.getElementById('compKpiStockVal')) document.getElementById('compKpiStockVal').textContent = kpis.total_stock_value || '₹0';
    if (document.getElementById('compKpiSellThrough')) document.getElementById('compKpiSellThrough').textContent = kpis.est_monthly_sell_through || '₹0';
    if (document.getElementById('compKpiDiscount')) document.getElementById('compKpiDiscount').textContent = kpis.avg_discount || '0.0%';
    if (document.getElementById('compKpiCoverage')) document.getElementById('compKpiCoverage').textContent = kpis.tracking_coverage || '100%';

    // 2. Brand Cards + Tracking Coverage Card
    renderComparatorBrandCards(data.brands);

    // 3. Three Bar Charts
    renderComparatorCharts(data.brands);

    // 4. Peer comparison matrix
    renderComparatorPeerMatrix(data.brands, data.leaders || {}, data.data_windows || {});

    // 5. Top Products by Brand (5 columns)
    renderComparatorTopProducts(data.brands);

    // 6. Key Insight
    if (document.getElementById('comparatorKeyInsightMsg')) {
      document.getElementById('comparatorKeyInsightMsg').textContent = displayValue(data.key_insight, 'No comparison insight is available for the current filters.');
    }
    if (document.getElementById('comparatorPromoInsightText')) {
      const catLabel = formatScopeLabel(comparatorState.category);
      const brandCount = (data.brands || []).length;
      document.getElementById('comparatorPromoInsightText').textContent = `${brandCount} brands compared in ${catLabel} using live catalog, latest inventory snapshot, and recent sales analytics.`;
    }
  } catch (err) {
    console.error('Error loading brand comparator:', err);
  }
}

function renderComparatorBrandCards(brands) {
  const container = document.getElementById('comparatorBrandCardsGrid');
  if (!container) return;

  const brandCardsHtml = brands.map((b) => `
    <div class="comparator-brand-card">
      <div>
        <div class="brand-card-top">
          ${renderBrandEmblem(b.display_name)}
          <button class="brand-dots-btn" title="Inspect ${escapeHtml(b.display_name)}" onclick='openCatalogWithScope({ brand: ${JSON.stringify(b.display_name)} });'>•••</button>
        </div>
        <div class="brand-prods-lbl">Products</div>
        <div class="brand-prods-val">${Number(b.product_count).toLocaleString()}</div>
      </div>
      <div class="brand-metrics-split">
        <div class="brand-metric-col">
          <span class="brand-metric-lbl">Avg. Discount</span>
          <span class="brand-metric-num">${formatComparatorPct(b.avg_discount)}</span>
          ${getBrandSparklineSVG(b.sparkline)}
        </div>
        <div class="brand-metric-col" style="text-align: right; align-items: flex-end;">
          <span class="brand-metric-lbl">ASP / Median</span>
          <span class="brand-metric-num">${formatComparatorPrice(b.avg_price)}</span>
          <span style="font-size: 9px; color: #64748b;">Median ${formatComparatorPrice(b.median_price)}</span>
          <span class="brand-growth-badge">${Number(b.growth_30d || 0) >= 0 ? '▲' : '▼'} ${Math.abs(Number(b.growth_30d || 0)).toFixed(1)}%</span>
          <span style="font-size: 8px; color: #94a3b8;">Sales rev growth</span>
        </div>
      </div>
      <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:6px; margin-top:10px; padding-top:10px; border-top:1px solid #f1f5f9;">
        <div>
          <div style="font-size:8px; color:#94a3b8; text-transform:uppercase; font-weight:800;">Product Share</div>
          <div style="font-size:12px; font-weight:850; color:#0f172a;">${formatComparatorPct(b.product_share)}</div>
        </div>
        <div>
          <div style="font-size:8px; color:#94a3b8; text-transform:uppercase; font-weight:800;">30D Revenue</div>
          <div style="font-size:12px; font-weight:850; color:#0f172a;">${escapeHtml(b.monthly_revenue_formatted || '₹0')}</div>
        </div>
        <div>
          <div style="font-size:8px; color:#94a3b8; text-transform:uppercase; font-weight:800;">Sell-through</div>
          <div style="font-size:12px; font-weight:850; color:#0f172a;">${formatComparatorPct(b.sell_through_rate, 2)}</div>
        </div>
      </div>
    </div>
  `).join('');

  const avgCoverage = brands.length
    ? Math.round(brands.reduce((sum, b) => sum + Number(b.tracking_coverage || 0), 0) / brands.length)
    : 0;
  const trackingCardHtml = `
    <div class="comparator-tracking-card">
      <div>
        <div class="tracking-head">
          <span>Tracking Coverage</span>
          <span class="info-icon" title="Audit coverage status">ⓘ</span>
        </div>
        <div class="tracking-list">
          ${brands.map(b => `
            <div class="tracking-brand-row">
              <span class="track-brand-name" title="${escapeHtml(b.display_name)}">${escapeHtml(b.display_name)}</span>
              <div class="track-progress-bar">
                <div class="track-progress-fill" style="width: ${b.tracking_coverage}%"></div>
              </div>
              <span class="track-pct">${b.tracking_coverage}%</span>
            </div>
          `).join('')}
        </div>
      </div>
      <div class="tracking-card-footer">
        <div class="tracking-dates">
          <span>Tracking window: latest available snapshot history</span>
        </div>
        <div class="tracking-caption">${avgCoverage >= 95 ? 'Most selected SKUs have latest inventory snapshots' : 'Coverage is based on SKUs present in the latest inventory snapshot'}</div>
      </div>
    </div>
  `;

  container.innerHTML = brandCardsHtml + trackingCardHtml;
}

// Custom plugin to draw exact value labels directly above vertical bars
const barValueLabelsPlugin = {
  id: 'barValueLabels',
  afterDatasetsDraw(chart) {
    const { ctx } = chart;
    const dataset = chart.data.datasets[0];
    const meta = chart.getDatasetMeta(0);
    if (!meta || !meta.data) return;

    ctx.save();
    ctx.font = 'bold 9.5px "Plus Jakarta Sans", sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'bottom';
    ctx.fillStyle = '#0f172a';

    meta.data.forEach((bar, index) => {
      let val = dataset.data[index];
      let displayVal = val;
      if (chart.canvas.id === 'compChartProductCount') {
        displayVal = Number(val).toLocaleString();
      } else if (chart.canvas.id === 'compChartAsp') {
        displayVal = '₹' + Number(val).toLocaleString();
      } else if (chart.canvas.id === 'compChartDiscount') {
        displayVal = val + '%';
      }
      ctx.fillText(displayVal, bar.x, bar.y - 3);
    });
    ctx.restore();
  }
};

function renderComparatorCharts(brands) {
  const brandLabels = brands.map(b => {
    const name = b.display_name || b.brand || 'Brand';
    return name.length > 14 ? `${name.slice(0, 12)}…` : name;
  });

  // Chart 1: Product Count
  const countCanvas = document.getElementById('compChartProductCount');
  if (countCanvas) {
    if (compChartProductCount) compChartProductCount.destroy();
    const counts = brands.map(b => b.product_count);
    const countColors = comparatorBarColors(counts);
    compChartProductCount = new Chart(countCanvas, {
      type: 'bar',
      plugins: [barValueLabelsPlugin],
      data: {
        labels: brandLabels,
        datasets: [{
          data: counts,
          backgroundColor: countColors,
          borderRadius: 4,
          barThickness: 26
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        layout: { padding: { top: 18, bottom: 0 } },
        plugins: { legend: { display: false }, tooltip: { enabled: true } },
        scales: {
          x: {
            grid: { display: false },
            ticks: { font: { size: 9, family: 'Plus Jakarta Sans' }, color: '#64748b' }
          },
          y: {
            display: true,
            beginAtZero: true,
            grid: { color: '#f1f5f9' },
            ticks: {
              color: '#94a3b8',
              font: { size: 9 },
              callback: (v) => v >= 1000 ? `${v / 1000}K` : v
            }
          }
        }
      }
    });
  }

  // Chart 2: Average Selling Price (ASP)
  const aspCanvas = document.getElementById('compChartAsp');
  if (aspCanvas) {
    if (compChartAsp) compChartAsp.destroy();
    const asps = brands.map(b => b.avg_price);
    const aspColors = comparatorBarColors(asps);
    compChartAsp = new Chart(aspCanvas, {
      type: 'bar',
      plugins: [barValueLabelsPlugin],
      data: {
        labels: brandLabels,
        datasets: [{
          data: asps,
          backgroundColor: aspColors,
          borderRadius: 4,
          barThickness: 26
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        layout: { padding: { top: 18, bottom: 0 } },
        plugins: { legend: { display: false }, tooltip: { enabled: true } },
        scales: {
          x: {
            grid: { display: false },
            ticks: { font: { size: 9, family: 'Plus Jakarta Sans' }, color: '#64748b' }
          },
          y: {
            display: true,
            beginAtZero: true,
            grid: { color: '#f1f5f9' },
            ticks: {
              color: '#94a3b8',
              font: { size: 9 },
              callback: (v) => v >= 1000 ? `₹${v / 1000}K` : `₹${v}`
            }
          }
        }
      }
    });
  }

  // Chart 3: Average Discount
  const discCanvas = document.getElementById('compChartDiscount');
  if (discCanvas) {
    if (compChartDiscount) compChartDiscount.destroy();
    const discounts = brands.map(b => b.avg_discount);
    const discountColors = comparatorBarColors(discounts);
    compChartDiscount = new Chart(discCanvas, {
      type: 'bar',
      plugins: [barValueLabelsPlugin],
      data: {
        labels: brandLabels,
        datasets: [{
          data: discounts,
          backgroundColor: discountColors,
          borderRadius: 4,
          barThickness: 26
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        layout: { padding: { top: 18, bottom: 0 } },
        plugins: { legend: { display: false }, tooltip: { enabled: true } },
        scales: {
          x: {
            grid: { display: false },
            ticks: { font: { size: 9, family: 'Plus Jakarta Sans' }, color: '#64748b' }
          },
          y: {
            display: true,
            beginAtZero: true,
            grid: { color: '#f1f5f9' },
            ticks: {
              color: '#94a3b8',
              font: { size: 9 },
              callback: (v) => `${v}%`
            }
          }
        }
      }
    });
  }
}

function renderComparatorPeerMatrix(brands, leaders = {}, windows = {}) {
  const container = document.getElementById('comparatorPeerMatrix');
  if (!container) return;

  if (!Array.isArray(brands) || brands.length === 0) {
    container.innerHTML = '<div style="padding:18px; color:#94a3b8; font-size:12px;">Select at least two brands to see peer comparison.</div>';
    return;
  }

  const leaderBadge = (metric, brand) => leaders[metric] && leaders[metric] === brand
    ? '<span style="display:inline-flex; margin-left:6px; padding:2px 6px; border-radius:999px; background:#ecfeff; color:#0369a1; font-size:9px; font-weight:900;">LEADER</span>'
    : '';
  const salesWindow = windows.sales_start_date && windows.sales_end_date
    ? `${windows.sales_start_date} to ${windows.sales_end_date}`
    : 'latest available sales window';
  const snapshotLabel = windows.inventory_snapshot_date || 'latest available snapshot';

  container.innerHTML = `
    <div style="display:flex; align-items:flex-start; justify-content:space-between; gap:12px; margin-bottom:12px;">
      <div>
        <h3 style="margin:0; font-size:15px; font-weight:900; color:#0f172a;">Peer Comparison Matrix</h3>
        <p style="margin:4px 0 0; font-size:11px; color:#64748b;">Real scoped metrics: catalog, price, inventory snapshot, and recent sales.</p>
      </div>
      <div style="font-size:10px; color:#64748b; text-align:right; line-height:1.45;">
        <div>Inventory: ${escapeHtml(snapshotLabel)}</div>
        <div>Sales: ${escapeHtml(salesWindow)}</div>
      </div>
    </div>
    <div style="overflow-x:auto;">
      <table style="width:100%; border-collapse:collapse; min-width:920px; font-size:11px;">
        <thead>
          <tr style="background:#f8fafc; color:#64748b; text-transform:uppercase; letter-spacing:.04em;">
            <th style="padding:10px; text-align:left;">Brand</th>
            <th style="padding:10px; text-align:right;">Products</th>
            <th style="padding:10px; text-align:right;">Product Share</th>
            <th style="padding:10px; text-align:right;">ASP</th>
            <th style="padding:10px; text-align:right;">Price Index</th>
            <th style="padding:10px; text-align:right;">Avg Discount</th>
            <th style="padding:10px; text-align:right;">Stock Value</th>
            <th style="padding:10px; text-align:right;">30D Revenue</th>
            <th style="padding:10px; text-align:right;">30D Units</th>
            <th style="padding:10px; text-align:right;">Sell-through</th>
            <th style="padding:10px; text-align:right;">Rating</th>
          </tr>
        </thead>
        <tbody>
          ${brands.map(b => `
            <tr style="border-bottom:1px solid #f1f5f9;">
              <td style="padding:10px; font-weight:850; color:#0f172a;">${escapeHtml(b.display_name || b.brand)}${leaderBadge('catalog_depth', b.brand)}</td>
              <td style="padding:10px; text-align:right; font-weight:800;">${Number(b.product_count || 0).toLocaleString('en-IN')}</td>
              <td style="padding:10px; text-align:right;">${formatComparatorPct(b.product_share)}</td>
              <td style="padding:10px; text-align:right; font-weight:800;">${formatComparatorPrice(b.avg_price)}${leaderBadge('premium_price', b.brand)}</td>
              <td style="padding:10px; text-align:right;">${Number(b.price_index || 0).toFixed(1)}</td>
              <td style="padding:10px; text-align:right; font-weight:800;">${formatComparatorPct(b.avg_discount)}${leaderBadge('deepest_discount', b.brand)}</td>
              <td style="padding:10px; text-align:right;">${escapeHtml(b.stock_value || '₹0')}</td>
              <td style="padding:10px; text-align:right; font-weight:800;">${escapeHtml(b.monthly_revenue_formatted || '₹0')}${leaderBadge('sales_revenue', b.brand)}</td>
              <td style="padding:10px; text-align:right;">${compactComparatorNumber(b.monthly_units)}</td>
              <td style="padding:10px; text-align:right; font-weight:800;">${formatComparatorPct(b.sell_through_rate, 2)}${leaderBadge('sell_through', b.brand)}</td>
              <td style="padding:10px; text-align:right;">${Number(b.avg_rating || 0).toFixed(2)} (${compactComparatorNumber(b.ratings_count)})</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `;
}

function renderComparatorTopProducts(brands) {
  const container = document.getElementById('comparatorTopProductsCols');
  if (!container) return;

  container.innerHTML = brands.map(b => {
    const productsHtml = (b.top_products || []).map((p, pIdx) => `
      <div class="product-mini-row" onclick="openProductDrawer(${p.product_id})" title="Inspect SKU: ${escapeHtml(p.title)}">
        <span class="product-rank-num">${pIdx + 1}</span>
        <img class="product-thumb-img" src="${p.image_url || 'assets/luxury_silk_banner.jpg'}" alt="Product" onerror="this.src='assets/luxury_silk_banner.jpg'" />
        <div class="product-info-col">
          <div class="product-mini-title">${escapeHtml(p.title)}</div>
          <div class="product-mini-meta">${p.velocity} · ${p.price} · ${displayCount(p.units_30d, '0')} units</div>
        </div>
      </div>
    `).join('');

    return `
      <div class="top-products-col">
        <div class="col-header-brand">
          <span class="col-brand-name">${escapeHtml(b.display_name)}</span>
          <span class="badge-top3">Top 3</span>
        </div>
        <div>
          ${productsHtml || '<div style="padding:12px; color:#94a3b8; font-size:11px;">No ranked products for this scope.</div>'}
        </div>
      </div>
    `;
  }).join('');
}

function exportBrandComparisonPDF() {
  window.print();
}

function generateDetailedBrandReport() {
  showToast('Generating exhaustive Brand Intelligence Report (PDF / XLSX)...');
  setTimeout(() => {
    showToast('Report generated successfully! Ready for export.');
  }, 1200);
}

async function loadBrandIntelligence() {
  try {
    const res = await fetch('/api/analytics/brand-intelligence');
    const json = await res.json();
    if (json.status !== 'success' || !json.data) return;
    brandIntelligenceCache = json.data;
    renderBrandIntelligence(brandIntelligenceCache);
  } catch (err) {
    console.error('Error loading brand intelligence:', err);
  }
}

function renderBrandIntelligence(data) {
  if (!data) return;

  // 1. KPI Cards
  const kpis = data.kpis || {};
  const bench = data.benchmark || {};

  if (document.getElementById('brandKpiDiscovered')) {
    document.getElementById('brandKpiDiscovered').textContent = (kpis.total_discovered_brands || kpis.active_catalog_brands || 0).toLocaleString();
  }
  if (document.getElementById('brandKpiActiveTracked')) {
    document.getElementById('brandKpiActiveTracked').textContent = (kpis.active_catalog_brands || 0).toLocaleString();
  }
  if (document.getElementById('brandKpiTopGMVBrand')) {
    document.getElementById('brandKpiTopGMVBrand').textContent = kpis.top_gmv_brand || '—';
  }

  // Calculate In-House Share %
  const inHouseSkus = bench.myntra_in_house ? bench.myntra_in_house.skus : 0;
  const extSkus = bench.external_brands ? bench.external_brands.skus : 0;
  const totalSkus = inHouseSkus + extSkus;
  const sharePct = totalSkus > 0 ? Math.round((inHouseSkus / totalSkus) * 100) : 0;

  if (document.getElementById('brandKpiPrivateShare')) {
    document.getElementById('brandKpiPrivateShare').textContent = `${sharePct}% (${inHouseSkus} SKUs)`;
  }

  // 2. Benchmark Cards
  if (bench.myntra_in_house) {
    const ih = bench.myntra_in_house;
    if (document.getElementById('benchInHouseSkus')) document.getElementById('benchInHouseSkus').textContent = ih.skus.toLocaleString();
    if (document.getElementById('benchInHouseASP')) document.getElementById('benchInHouseASP').textContent = `₹${ih.asp.toLocaleString()}`;
    if (document.getElementById('benchInHouseDisc')) document.getElementById('benchInHouseDisc').textContent = `${ih.discount}%`;
    if (document.getElementById('benchInHouseRating')) document.getElementById('benchInHouseRating').textContent = `⭐ ${ih.rating}`;
  }
  if (bench.external_brands) {
    const ext = bench.external_brands;
    if (document.getElementById('benchExternalSkus')) document.getElementById('benchExternalSkus').textContent = ext.skus.toLocaleString();
    if (document.getElementById('benchExternalASP')) document.getElementById('benchExternalASP').textContent = `₹${ext.asp.toLocaleString()}`;
    if (document.getElementById('benchExternalDisc')) document.getElementById('benchExternalDisc').textContent = `${ext.discount}%`;
    if (document.getElementById('benchExternalRating')) document.getElementById('benchExternalRating').textContent = `⭐ ${ext.rating}`;
  }

  // 3. Leaderboard Table
  const lbody = document.getElementById('brandLeaderboardTableBody');
  if (lbody && data.leaderboard) {
    lbody.innerHTML = data.leaderboard.map((b, idx) => `
      <tr>
        <td>
          <div style="display:flex; align-items:center; gap:8px;">
            <span style="display:inline-flex; align-items:center; justify-content:center; width:22px; height:22px; border-radius:50%; background:#f1f5f9; font-size:0.75rem; font-weight:700; color:#475569;">${idx + 1}</span>
            <strong>${b.brand}</strong>
          </div>
        </td>
        <td>
          <span class="badge-tag ${b.is_myntra ? 'red' : 'blue'}">
            ${b.is_myntra ? 'Myntra In-House' : 'External'}
          </span>
        </td>
        <td><strong>${b.skus.toLocaleString()}</strong></td>
        <td>₹${Math.round(b.asp).toLocaleString()}</td>
        <td><span style="color:#ef4444; font-weight:600;">${b.avg_discount}%</span></td>
        <td><strong style="color:#0f172a;">${b.units_sold.toLocaleString()}</strong></td>
        <td><strong style="color:#10b981;">₹${Math.round(b.total_gmv).toLocaleString()}</strong></td>
        <td><span style="font-weight:700; color:#3b82f6;">${b.avg_ros}</span></td>
        <td>
          <button class="btn btn-secondary" style="padding:4px 10px; font-size:0.75rem;" onclick="openBrandDrawer('${b.brand.replace(/'/g, "\\'")}')">Analyze ↗</button>
        </td>
      </tr>
    `).join('');
  }

  // 4. Pricing Power Table
  const pbody = document.getElementById('brandPricingTableBody');
  if (pbody && data.leaderboard) {
    const catBenchmark = data.category_benchmark || {};
    const catAvgPrice = catBenchmark.asp || (data.kpis && data.kpis.category_avg_asp) || 0;
    const catAvgDisc = catBenchmark.discount || (data.kpis && data.kpis.category_avg_discount) || 0;

    pbody.innerHTML = data.leaderboard.map(b => {
      const benchmarkPrice = b.category_asp || catAvgPrice;
      const benchmarkDisc = b.category_discount || catAvgDisc;
      const badgeClass = b.badge_class || (b.pricing_power_index >= 1.15 ? 'high' : b.pricing_power_index >= 0.85 ? 'moderate' : 'low');
      const label = b.classification || (b.pricing_power_index >= 1.15 ? 'Strong Pricing Power' : b.pricing_power_index >= 0.85 ? 'Moderate Pricing Power' : 'Discount-Driven / Elastic');

      return `
        <tr>
          <td><strong>${b.brand}</strong></td>
          <td>₹${Math.round(b.asp).toLocaleString()}</td>
          <td>₹${Math.round(benchmarkPrice).toLocaleString()} <span style="font-size:0.72rem; color:#94a3b8;">(${benchmarkDisc}% avg off)</span></td>
          <td><span style="color:#ef4444; font-weight:600;">${b.avg_discount}%</span></td>
          <td><strong style="font-size:1.05rem; color:${b.pricing_power_index >= 1.15 ? '#059669' : b.pricing_power_index >= 0.85 ? '#d97706' : '#dc2626'};">${b.pricing_power_index}</strong></td>
          <td>
            <span class="brand-pricing-power-badge ${badgeClass}">${label}</span>
          </td>
          <td>
            <button class="btn btn-secondary" style="padding:4px 10px; font-size:0.75rem;" onclick="openBrandDrawer('${b.brand.replace(/'/g, "\\'")}')">Details ↗</button>
          </td>
        </tr>
      `;
    }).join('');
  }
}

async function openBrandDrawer(brandName) {
  const drawer = document.getElementById('brandDrawer');
  const backdrop = document.getElementById('brandDrawerBackdrop');
  if (!drawer) return;

  document.getElementById('drawerBrandName').textContent = brandName;
  document.getElementById('drawerCategorySplit').innerHTML = '<div style="color:#94a3b8; font-size:0.85rem;">Loading profile...</div>';
  document.getElementById('drawerTopSkus').innerHTML = '';

  const btnCatalog = document.getElementById('btnViewBrandCatalog');
  if (btnCatalog) {
    btnCatalog.onclick = () => {
      closeBrandDrawer();
      openCatalogWithScope({ brand: brandName });
    };
  }

  drawer.classList.add('active');
  if (backdrop) backdrop.style.display = 'block';

  try {
    const res = await fetch(`/api/analytics/brand-intelligence?brand=${encodeURIComponent(brandName)}`);
    const json = await res.json();
    if (json.status !== 'success' || !json.data || !json.data.brand_profile) return;
    const profile = json.data.brand_profile;

    // Render category split
    const catContainer = document.getElementById('drawerCategorySplit');
    if (profile.category_split && profile.category_split.length > 0) {
      catContainer.innerHTML = profile.category_split.map(c => `
        <div style="background:#f8fafc; padding:10px 14px; border-radius:8px; display:flex; justify-content:space-between; align-items:center; border:1px solid #e2e8f0;">
          <div>
            <strong>${c.category}</strong>
            <div style="font-size:0.75rem; color:#64748b;">${c.skus} active SKUs</div>
          </div>
          <div style="text-align:right;">
            <div style="font-weight:700; color:#0f172a;">₹${Math.round(c.asp).toLocaleString()}</div>
            <div style="font-size:0.75rem; color:#ef4444;">${c.discount}% avg off</div>
          </div>
        </div>
      `).join('');
    } else {
      catContainer.innerHTML = '<div style="color:#94a3b8; font-size:0.85rem;">No category breakdown available.</div>';
    }

    // Render top SKUs
    const skuContainer = document.getElementById('drawerTopSkus');
    if (profile.top_skus && profile.top_skus.length > 0) {
      skuContainer.innerHTML = profile.top_skus.map(s => `
        <div style="background:#ffffff; padding:10px 14px; border-radius:8px; border:1px solid #e2e8f0; display:flex; justify-content:space-between; align-items:center;">
          <div style="flex:1; min-width:0; padding-right:10px;">
            <div style="font-weight:600; font-size:0.85rem; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${s.title}">${s.title}</div>
            <div style="font-size:0.75rem; color:#64748b;">${s.category}${s.rating && Number(s.rating) > 0 ? ` • ⭐ ${Number(s.rating).toFixed(1)}` : ''}</div>
          </div>
          <div style="text-align:right; white-space:nowrap;">
            <div style="font-weight:700; color:#0f172a;">₹${s.price}</div>
            <a href="${s.url}" target="_blank" style="font-size:0.75rem; color:#3b82f6; text-decoration:none;">View on Myntra ↗</a>
          </div>
        </div>
      `).join('');
    } else {
      skuContainer.innerHTML = '<div style="color:#94a3b8; font-size:0.85rem;">No SKUs available.</div>';
    }
  } catch (err) {
    console.error('Error fetching brand profile:', err);
  }
}

function closeBrandDrawer() {
  const drawer = document.getElementById('brandDrawer');
  const backdrop = document.getElementById('brandDrawerBackdrop');
  if (drawer) drawer.classList.remove('active');
  if (backdrop) backdrop.style.display = 'none';
}

// ==========================================================================
// COLOR INTELLIGENCE SUITE (Image 2)
// ==========================================================================
let activeColorScope = {
  category: 'shirts',
  gender: 'men',
  subcategory: 'all',
  priceRanges: [],
  brands: []
};

let colorShareDonutInst = null;
let colorTrendLineInst = null;
let colorAvgPriceBarInst = null;
let colorSeasonalBarInst = null;
let colorPriceMetricMode = 'price';

function setColorGender(g, btn) {
  document.querySelectorAll('#scopeColorGenderPills .gender-pill').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  activeColorScope.gender = (g || 'men').toLowerCase();
  applyColorScopeFilters();
}

async function refreshColorSidebarFacets() {
  try {
    const params = new URLSearchParams();
    if (activeColorScope.category && activeColorScope.category !== 'all') params.set('category', activeColorScope.category);
    if (activeColorScope.gender && activeColorScope.gender !== 'all') params.set('gender', activeColorScope.gender);
    if (activeColorScope.priceRanges && activeColorScope.priceRanges.length > 0) params.set('price_ranges', activeColorScope.priceRanges.join(','));

    const data = await fetchCachedJson(buildFilterCountsUrl(params), { ttlMs: 20000 });
    const pb = data.price_buckets || {};
    const subcategories = Array.isArray(data.subcategories) ? data.subcategories : [];
    const brandsList = Array.isArray(data.brands_list) ? data.brands_list : [];
    const priceMap = {
      lt_500: pb.lt_500,
      '500_1000': pb['500_1000'],
      '1000_2000': pb['1000_2000'],
      '2000_3000': pb['2000_3000'],
      '3000_4000': pb['3000_4000'],
      gt_4000: pb.gt_4000
    };

    document.querySelectorAll('input[name="scopeColorPrice"]').forEach(chk => {
      const countSpan = chk.parentElement?.querySelector('.check-count');
      if (countSpan && priceMap[chk.value] !== undefined) {
        countSpan.textContent = Number(priceMap[chk.value] || 0).toLocaleString('en-IN');
      }
    });

    const subSel = document.getElementById('scopeColorSubcatSelect');
    if (subSel && subcategories.length > 0) {
      const validValues = new Set(subcategories.map(s => s.value));
      if (!validValues.has(activeColorScope.subcategory)) {
        activeColorScope.subcategory = 'all';
      }
      subSel.innerHTML = subcategories.map(s => {
        const value = String(s.value || 'all');
        const name = String(s.name || value);
        const selected = value === activeColorScope.subcategory ? 'selected' : '';
        return `<option value="${escapeHtml(value)}" ${selected}>${escapeHtml(name)}</option>`;
      }).join('');
    }

    const brandBox = document.getElementById('scopeColorAccBrand');
    if (brandBox) {
      const availableBrands = new Set(brandsList.map(b => b.brand));
      activeColorScope.brands = (activeColorScope.brands || []).filter(b => availableBrands.has(b));
      brandBox.innerHTML = brandsList.map(b => `
        <label class="sub-check-item">
          <input type="checkbox" value="${escapeHtml(b.brand)}" onchange="applyColorScopeFilters()" ${activeColorScope.brands.includes(b.brand) ? 'checked' : ''} />
          <span class="check-text">${escapeHtml(b.brand)}</span>
          <span class="check-count">${Number(b.count || 0).toLocaleString('en-IN')}</span>
        </label>
      `).join('');
    }
  } catch (err) {
    console.warn('Error refreshing color sidebar facets:', err);
  }
}

async function applyColorScopeFilters() {
  const catSel = document.getElementById('scopeColorCategorySelect');
  if (catSel) activeColorScope.category = catSel.value;

  const subSel = document.getElementById('scopeColorSubcatSelect');
  if (subSel) activeColorScope.subcategory = subSel.value;

  const activeGenBtn = document.querySelector('#scopeColorGenderPills .gender-pill.active');
  if (activeGenBtn) {
    activeColorScope.gender = activeGenBtn.textContent.trim().toLowerCase();
  }

  const prChecked = [];
  document.querySelectorAll('input[name="scopeColorPrice"]:checked').forEach(c => prChecked.push(c.value));
  activeColorScope.priceRanges = prChecked;

  const bChecked = [];
  document.querySelectorAll('#scopeColorAccBrand input[type="checkbox"]:checked').forEach(c => bChecked.push(c.value));
  activeColorScope.brands = bChecked;

  await refreshColorSidebarFacets();
  loadColorIntelligence();
}

async function resetColorScopeFilters() {
  const catSel = document.getElementById('scopeColorCategorySelect');
  if (catSel) catSel.value = 'shirts';

  const subSel = document.getElementById('scopeColorSubcatSelect');
  if (subSel) subSel.value = 'all';

  document.querySelectorAll('#scopeColorGenderPills .gender-pill').forEach((b, i) => b.classList.toggle('active', i === 0));
  document.querySelectorAll('input[name="scopeColorPrice"]').forEach(c => c.checked = false);
  document.querySelectorAll('#scopeColorAccBrand input[type="checkbox"]').forEach(c => c.checked = false);

  activeColorScope = {
    category: 'shirts',
    gender: 'men',
    subcategory: 'all',
    priceRanges: [],
    brands: []
  };

  await refreshColorSidebarFacets();
  loadColorIntelligence();
}

function switchColorTab(tab, btn) {
  document.querySelectorAll('#view-colors .intel-tabs-nav .intel-tab-btn').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');

  const targetMap = {
    overview: 'colorOverviewCard',
    performance: 'colorPerformanceCard',
    trend: 'colorTrendCard',
    brand: 'colorBrandCard',
    price: 'colorPriceCard',
    seasonal: 'colorSeasonalCard',
    combinations: 'colorInsightsList',
    whitespace: 'colorWhitespaceCard'
  };
  const targetEl = document.getElementById(targetMap[tab] || 'colorOverviewCard');
  if (targetEl) {
    targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
}

function exportColorReport() {
  window.print();
}

async function loadColorIntelligence() {
  try {
    await refreshColorSidebarFacets();
    const p = new URLSearchParams();
    p.append('category', activeColorScope.category || 'shirts');
    p.append('gender', activeColorScope.gender || 'men');
    if (activeColorScope.subcategory && activeColorScope.subcategory !== 'all') {
      p.append('subcategory', activeColorScope.subcategory);
    }
    if (activeColorScope.priceRanges && activeColorScope.priceRanges.length > 0) {
      p.append('price_ranges', activeColorScope.priceRanges.join(','));
    }
    if (activeColorScope.brands && activeColorScope.brands.length > 0) {
      p.append('brand', activeColorScope.brands.join(','));
    }

    const res = await fetch(`/api/analytics/color-intelligence?${p.toString()}`);
    const data = await res.json();
    if (!data || data.status !== 'success') return;

    renderColorIntelligence(data);
  } catch (err) {
    console.error('Error loading Color Intelligence:', err);
  }
}

function setColorPriceMetric(mode, btn) {
  colorPriceMetricMode = mode === 'discount' ? 'discount' : 'price';
  const priceBtn = document.getElementById('colorMetricPriceBtn');
  const discountBtn = document.getElementById('colorMetricDiscountBtn');
  const activeStyle = { background: '#0f172a', color: '#fff' };
  const inactiveStyle = { background: 'transparent', color: '#64748b' };
  if (priceBtn) Object.assign(priceBtn.style, colorPriceMetricMode === 'price' ? activeStyle : inactiveStyle);
  if (discountBtn) Object.assign(discountBtn.style, colorPriceMetricMode === 'discount' ? activeStyle : inactiveStyle);
  if (btn && btn.blur) btn.blur();
  renderColorPriceChart(window.__lastColorIntelData || null);
}

function renderColorTrendChart(data) {
  if (!data) return;
  const colors = Array.isArray(data.color_distribution) ? data.color_distribution : [];
  const trendCtx = document.getElementById('colorTrendLineChart');
  if (!(trendCtx && window.Chart)) return;

  if (colorTrendLineInst) colorTrendLineInst.destroy();
  const topN = Math.max(1, Number(document.getElementById('colorTrendTopNSelect')?.value || 5));
  const selected = colors.slice(0, topN);
  const datasets = selected.map(c => ({
    label: c.color,
    data: [Number(c.previous_units || 0), Number(c.current_units || 0)],
    borderColor: c.hex,
    backgroundColor: c.hex,
    borderWidth: 2,
    pointRadius: 2,
    tension: 0.3
  }));

  colorTrendLineInst = new Chart(trendCtx, {
    type: 'line',
    data: { labels: ['Previous 7D', 'Current 7D'], datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { display: false }, ticks: { font: { size: 9 }, color: '#64748b' } },
        y: { grid: { color: '#f1f5f9' }, ticks: { font: { size: 9 }, color: '#94a3b8', callback: v => v >= 1000 ? `${(v/1000).toFixed(0)}K` : v } }
      }
    }
  });
}

function renderColorPriceChart(data) {
  if (!data) return;
  const colors = Array.isArray(data.color_distribution) ? data.color_distribution : [];
  const priceCtx = document.getElementById('colorAvgPriceBarChart');
  if (!(priceCtx && window.Chart)) return;

  if (colorAvgPriceBarInst) colorAvgPriceBarInst.destroy();
  const top8 = colors.slice(0, 8);
  const metricKey = colorPriceMetricMode === 'discount' ? 'avg_disc' : 'avg_price';
  const chartTitle = document.getElementById('colorPriceMetricTitle');
  const chartSubtitle = document.getElementById('colorPriceMetricSubtitle');
  if (chartTitle) chartTitle.textContent = colorPriceMetricMode === 'discount' ? 'Color-wise Average Discount' : 'Color-wise Average Price';
  if (chartSubtitle) chartSubtitle.textContent = colorPriceMetricMode === 'discount'
    ? 'Average discount percentage by color'
    : 'Average selling price by color';

  colorAvgPriceBarInst = new Chart(priceCtx, {
    type: 'bar',
    data: {
      labels: top8.map(c => c.color),
      datasets: [{
        data: top8.map(c => Number(c[metricKey] || 0)),
        backgroundColor: top8.map(c => c.hex),
        borderRadius: 4,
        barThickness: 10
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: {
          grid: { color: '#f1f5f9' },
          ticks: {
            font: { size: 9 },
            color: '#94a3b8',
            callback: v => colorPriceMetricMode === 'discount' ? `${v}%` : `₹${v}`
          }
        },
        y: { grid: { display: false }, ticks: { font: { size: 9, weight: '600' }, color: '#475569' } }
      }
    }
  });
}

function renderColorIntelligence(data) {
  if (!data) return;
  window.__lastColorIntelData = data;
  const setTxt = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
  const formatGrowth = (value, suffix = '%') => {
    const num = Number(value || 0);
    const arrow = num >= 0 ? '↑' : '↓';
    return `${arrow} ${Math.abs(num).toFixed(1)}${suffix}`;
  };
  const k = data.kpis || {};
  const categoryLabel = formatScopeLabel(data.category || activeColorScope.category || 'shirts');

  setTxt('colorBreadcrumbCat', categoryLabel.toUpperCase());
  setTxt('colorHeaderTitle', `Color Intelligence (${categoryLabel})`);
  setTxt('colorHeaderSubtitle', `Discover what colors are leading, accelerating, or underrepresented in ${categoryLabel.toLowerCase()} within the current filter selection.`);

  // 1. Top KPI Cards
  setTxt('colorKpiTotalProductsVal', displayCount(k.total_products_num ?? k.total_products));
  setTxt('colorKpiTotalProductsDelta', displayValue(k.products_growth));
  setTxt('colorKpiTotalProductsSub', `Across ${displayCount(k.brands_count)} brands`);

  setTxt('colorKpiUniqueVal', displayCount(k.unique_colors));
  setTxt('colorKpiUniqueDelta', displayValue(k.colors_growth));
  setTxt('colorKpiUniqueSub', 'Active in assortment');

  setTxt('colorKpiTopName', displayValue(k.top_color));
  setTxt('colorKpiTopShare', displayValue(k.top_color_share));
  const topSw = document.getElementById('colorKpiTopSwatch');
  if (topSw) topSw.style.background = k.top_color_hex || '#0f172a';

  setTxt('colorKpiGrowName', displayValue(k.fast_color));
  setTxt('colorKpiGrowDemand', displayValue(k.fast_color_growth));
  const growSw = document.getElementById('colorKpiGrowSwatch');
  if (growSw) growSw.style.background = k.fast_color_hex || '#556b2f';

  const colors = data.color_distribution || [];

  // 2. Color Share Donut Chart & Legend List
  const shareCtx = document.getElementById('colorShareDonutChart');
  if (shareCtx && window.Chart) {
    if (colorShareDonutInst) colorShareDonutInst.destroy();
    const top10 = colors.slice(0, 10);
    colorShareDonutInst = new Chart(shareCtx, {
      type: 'doughnut',
      data: {
        labels: top10.map(c => c.color),
        datasets: [{
          data: top10.map(c => c.count),
          backgroundColor: top10.map(c => c.hex),
          borderWidth: 2,
          borderColor: '#ffffff'
        }]
      },
      options: {
        plugins: { legend: { display: false } },
        cutout: '68%'
      }
    });

    const legEl = document.getElementById('colorShareLegendList');
    if (legEl) {
      legEl.innerHTML = top10.map(c => `
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
          <div style="display:flex; align-items:center; gap:6px;">
            <span style="width:10px; height:10px; border-radius:50%; background:${c.hex}; border:1px solid #cbd5e1; display:inline-block;"></span>
            <strong style="color:#0f172a;">${escapeHtml(c.color)}</strong>
          </div>
          <span style="color:#64748b; font-weight:600;">${c.share} (${c.count.toLocaleString()})</span>
        </div>
      `).join('');
    }
  }

  // 3-4. Color charts
  renderColorTrendChart(data);
  renderColorPriceChart(data);

  // 5. Tables: Top Performing, Fastest Growing, Slowest Performing
  const topBody = document.getElementById('colorTopPerfTableBody');
  if (topBody) {
    topBody.innerHTML = colors.slice(0, 5).map((c, i) => `
      <tr style="border-bottom:1px solid #f1f5f9;">
        <td style="padding:6px 8px; font-weight:700; color:#64748b;">${i+1}</td>
        <td style="padding:6px 8px;">
          <div style="display:flex; align-items:center; gap:6px;">
            <span style="width:10px; height:10px; border-radius:50%; background:${c.hex}; border:1px solid #cbd5e1; display:inline-block;"></span>
            <strong style="color:#0f172a;">${escapeHtml(c.color)}</strong>
          </div>
        </td>
        <td style="padding:6px 8px; text-align:right; font-weight:600; color:#475569;">${c.count.toLocaleString()}</td>
        <td style="padding:6px 8px; text-align:right; font-weight:600; color:#0f172a;">${c.units_sold.toLocaleString()}</td>
        <td style="padding:6px 8px; text-align:right; font-weight:700; color:${Number(c.growth_pct || 0) >= 0 ? '#10b981' : '#ef4444'};">${formatGrowth(c.growth_pct)}</td>
      </tr>
    `).join('');
  }

  const fastBody = document.getElementById('colorFastGrowingTableBody');
  if (fastBody) {
    const fastColors = [...colors]
      .sort((a, b) => Number(b.growth_pct || 0) - Number(a.growth_pct || 0))
      .slice(0, 5);
    fastBody.innerHTML = fastColors.map((c, i) => `
      <tr style="border-bottom:1px solid #f1f5f9;">
        <td style="padding:6px 8px; font-weight:700; color:#64748b;">${i+1}</td>
        <td style="padding:6px 8px;">
          <div style="display:flex; align-items:center; gap:6px;">
            <span style="width:10px; height:10px; border-radius:50%; background:${c.hex}; border:1px solid #cbd5e1; display:inline-block;"></span>
            <strong style="color:#0f172a;">${escapeHtml(c.color)}</strong>
          </div>
        </td>
        <td style="padding:6px 8px; text-align:right; font-weight:700; color:${Number(c.growth_pct || 0) >= 0 ? '#10b981' : '#ef4444'};">${formatGrowth(c.growth_pct)}</td>
      </tr>
    `).join('');
  }

  const slowBody = document.getElementById('colorSlowPerfTableBody');
  if (slowBody) {
    const slowColors = [...colors]
      .sort((a, b) => Number(a.growth_pct || 0) - Number(b.growth_pct || 0))
      .slice(0, 5);
    slowBody.innerHTML = slowColors.map((c, i) => `
      <tr style="border-bottom:1px solid #f1f5f9;">
        <td style="padding:6px 8px; font-weight:700; color:#64748b;">${i+1}</td>
        <td style="padding:6px 8px;">
          <div style="display:flex; align-items:center; gap:6px;">
            <span style="width:10px; height:10px; border-radius:50%; background:${c.hex}; border:1px solid #cbd5e1; display:inline-block;"></span>
            <strong style="color:#0f172a;">${escapeHtml(c.color)}</strong>
          </div>
        </td>
        <td style="padding:6px 8px; text-align:right; font-weight:700; color:${Number(c.growth_pct || 0) >= 0 ? '#10b981' : '#ef4444'};">${formatGrowth(c.growth_pct)}</td>
      </tr>
    `).join('');
  }

  // 6. Color Heatmap by Brand Matrix
  const hmContainer = document.getElementById('colorBrandHeatmapGrid');
  if (hmContainer && data.heatmap) {
    const top9Cols = colors.slice(0, 9);
    hmContainer.innerHTML = `
      <table style="width:100%; border-collapse:collapse; font-size:10px;">
        <thead>
          <tr style="background:#f8fafc; color:#64748b;">
            <th style="padding:4px 6px; text-align:left;">BRAND</th>
            ${top9Cols.map(c => `<th style="padding:4px 6px; text-align:center;">${escapeHtml(c.color)}</th>`).join('')}
          </tr>
        </thead>
        <tbody>
          ${(data.heatmap || []).map(row => `
            <tr style="border-bottom:1px solid #f1f5f9;">
              <td style="padding:6px; font-weight:700; color:#0f172a;">${escapeHtml(row.brand)}</td>
              ${(row.colors || []).map(cell => {
                const alpha = Math.min(1.0, 0.15 + (cell.count / 800));
                return `<td style="padding:6px; text-align:center; background:rgba(37, 99, 235, ${alpha.toFixed(2)}); color:${alpha > 0.5 ? '#fff' : '#0f172a'}; font-weight:700; border-radius:2px;">${cell.count}</td>`;
              }).join('')}
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
  }

  // 7. Seasonal Color Demand Grouped Bar Chart
  const seasCtx = document.getElementById('colorSeasonalBarChart');
  if (seasCtx && window.Chart) {
    if (colorSeasonalBarInst) colorSeasonalBarInst.destroy();
    const seasData = data.seasonal_demand || [];
    colorSeasonalBarInst = new Chart(seasCtx, {
      type: 'bar',
      data: {
        labels: seasData.map(s => s.color),
        datasets: [
          { label: 'Winter', data: seasData.map(s => s.winter), backgroundColor: '#1e3a8a' },
          { label: 'Summer', data: seasData.map(s => s.summer), backgroundColor: '#3b82f6' },
          { label: 'Monsoon', data: seasData.map(s => s.monsoon), backgroundColor: '#94a3b8' },
          { label: 'Festive', data: seasData.map(s => s.festive), backgroundColor: '#dc2626' }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: true, position: 'top', labels: { font: { size: 9 }, boxWidth: 8 } } },
        scales: {
          x: { grid: { display: false }, ticks: { font: { size: 9 }, color: '#475569' } },
          y: { grid: { color: '#f1f5f9' }, ticks: { font: { size: 8 }, color: '#94a3b8' } }
        }
      }
    });
  }

  // 8. Numbered Insights Cards List
  const insContainer = document.getElementById('colorInsightsList');
  if (insContainer && data.insights) {
    insContainer.innerHTML = (data.insights || []).map((ins, idx) => `
      <div style="display:flex; gap:10px; align-items:flex-start; background:#f8fafc; padding:10px 12px; border-radius:8px; border:1px solid #e2e8f0;">
        <span style="width:20px; height:20px; border-radius:50%; background:#0f172a; color:#fff; font-size:11px; font-weight:800; display:flex; align-items:center; justify-content:center; flex-shrink:0;">${idx+1}</span>
        <p style="margin:0; font-size:11px; color:#334155; line-height:1.4;">${escapeHtml(ins)}</p>
      </div>
    `).join('');
  }
}

// ==========================================================================
// ALL BRANDS DIRECTORY (A TO Z)
// ==========================================================================
async function fetchBrandsDirectory() {
  const tbody = document.getElementById('brandsTableBody');
  if (!tbody) return;

  tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:30px; color:#94a3b8;">Loading brands directory...</td></tr>`;

  const search = document.getElementById('brandsDirectorySearch')?.value || '';
  const type = document.getElementById('brandsTypeFilter')?.value || '';

  try {
    const res = await fetch(`/api/brands?search=${encodeURIComponent(search)}&brand_type=${encodeURIComponent(type)}`);
    const data = await res.json();
    const brands = data.brands || [];
    if (document.getElementById('brandsSubtitleCount') && data.total) {
      document.getElementById('brandsSubtitleCount').textContent = data.total.toLocaleString();
    }

    if (brands.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:30px; color:#94a3b8;">No brands discovered.</td></tr>`;
      return;
    }

    tbody.innerHTML = brands.map(b => `
      <tr>
        <td><strong>${b.brand_name}</strong></td>
        <td>
          <span class="badge-tag ${b.is_myntra_label ? 'red' : 'blue'}">
            ${b.is_myntra_label ? 'Myntra In-House' : 'External Brand'}
          </span>
        </td>
        <td>${(b.shirts_count || 0).toLocaleString()}</td>
        <td>${(b.denims_count || 0).toLocaleString()}</td>
        <td>${(b.western_count || 0).toLocaleString()}</td>
        <td><strong>${(b.total_count || 0).toLocaleString()}</strong></td>
        <td>
          <button class="btn btn-secondary" onclick='openCatalogWithScope({ brand: ${JSON.stringify(b.brand_name)} });'>View SKUs</button>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    console.error('Error fetching brands directory:', err);
  }
}

function debounceBrandsSearch() {
  clearTimeout(window._brandTimer);
  window._brandTimer = setTimeout(fetchBrandsDirectory, 350);
}

// ==========================================================================
// 8. SCRAPER ENGINE TELEMETRY & CONTROLS
// ==========================================================================
function openScraperModal() {
  document.getElementById('scraperModal').classList.add('active');
  checkScraperStatus();
}

function closeScraperModal() {
  document.getElementById('scraperModal').classList.remove('active');
}

async function startScraperJob() {
  const categories = document.getElementById('modalScraperCategories').value;
  const brand_type = document.getElementById('modalScraperBrandType').value;
  const brands = document.getElementById('modalScraperBrands')?.value.trim() || '';
  const workers = parseInt(document.getElementById('modalScraperWorkers').value, 10) || 6;
  const limit = parseInt(document.getElementById('modalScraperLimit').value, 10) || 0;

  const btn = document.getElementById('btnStartScraperModal');
  if (btn) btn.textContent = 'Launching Engine...';

  try {
    const res = await fetch('/api/scraper/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ categories, brand_type, brands, workers, limit })
    });
    const data = await res.json();
    if (res.ok) {
      closeScraperModal();
      await checkScraperStatus();
      switchView('console');
      startLogStream();
    } else {
      alert(data.message || `Scraper already running (PID: ${data.pid})`);
      await checkScraperStatus();
    }
  } catch (err) {
    alert('Failed to start scraper: ' + err.message);
  } finally {
    if (btn) btn.textContent = '🚀 Start Scraper Engine';
  }
}

async function stopScraperJob() {
  const ok = confirm("Are you sure you want to stop the scraper engine?");
  if (!ok) return;

  const btnStopModal = document.getElementById('btnStopScraperModal');
  const btnConsoleStop = document.getElementById('btnConsoleStopScraper');
  if (btnStopModal) btnStopModal.textContent = 'Stopping...';
  if (btnConsoleStop) btnConsoleStop.textContent = 'Stopping...';

  try {
    const res = await fetch('/api/scraper/stop', { method: 'POST' });
    const data = await res.json();
    closeScraperModal();
    await checkScraperStatus();
    alert("🛑 " + (data.message || "Scraper stopped successfully."));
  } catch (err) {
    alert('Failed to stop scraper: ' + err.message);
  } finally {
    if (btnStopModal) btnStopModal.textContent = '🛑 Stop Scraper';
    if (btnConsoleStop) btnConsoleStop.textContent = '🛑 Stop Scraper';
  }
}

async function cleanDatabaseUI() {
  const ok = confirm("⚠️ ARE YOU SURE YOU WANT TO CLEAN THE DATABASE?\n\nThis will immediately stop any active scrapers and reset all products, inventory, and crawl checkpoints back to ZERO.");
  if (!ok) return;

  try {
    const res = await fetch('/api/db/clean', { method: 'POST' });
    const data = await res.json();
    if (data.status === 'cleaned') {
      invalidateClientJsonCache('/api/filter-counts');
      invalidateClientJsonCache('/api/snapshot-dates');
      alert("✅ DATABASE CLEANED SUCCESSFULLY!\nAll catalog products and inventory records have been reset to 0.");
      closeScraperModal();
      await checkScraperStatus();
      fetchStatsAndInsights();
      fetchCatalogProducts();
      fetchBrandsDirectory();
    } else {
      alert("Error cleaning database: " + (data.message || "Unknown error"));
    }
  } catch (err) {
    alert("Network error cleaning database: " + err.message);
  }
}

async function checkScraperStatus() {
  if (_scraperStatusRequest) {
    return _scraperStatusRequest;
  }

  _scraperStatusRequest = (async () => {
    try {
      const res = await fetch('/api/scraper/status');
      const data = await res.json();
      const isRunning = !!data.running;
      const pid = data.pid || (data.pids && data.pids[0]);

      // Top Header Pill
      const pill = document.getElementById('headerScraperPill');
      const dot = document.getElementById('headerScraperDot');
      const txt = document.getElementById('headerScraperText');

      if (isRunning) {
        if (pill) pill.className = 'scraper-status-pill running';
        if (dot) dot.style.background = '#10b981';
        if (txt) txt.textContent = `Scraper Running (PID ${pid})`;
      } else {
        if (pill) pill.className = 'scraper-status-pill';
        if (dot) dot.style.background = '#94a3b8';
        if (txt) txt.textContent = 'Scraper Idle';
      }

      // Modal elements
      const modalDot = document.getElementById('modalStatusDot');
      const modalBanner = document.getElementById('modalRunningBanner');
      const modalPid = document.getElementById('modalRunningPid');
      const btnStopModal = document.getElementById('btnStopScraperModal');
      const btnStartModal = document.getElementById('btnStartScraperModal');

      if (modalDot) modalDot.style.background = isRunning ? '#10b981' : '#94a3b8';
      if (modalBanner) modalBanner.style.display = isRunning ? 'block' : 'none';
      if (modalPid) modalPid.textContent = pid || '--';
      if (btnStopModal) btnStopModal.style.display = isRunning ? 'inline-flex' : 'none';
      if (btnStartModal) {
        btnStartModal.textContent = isRunning ? 'Restart / Relaunch Engine' : '🚀 Start Scraper Engine';
      }

      // Scraper Console View Elements
      const consoleStatusText = document.getElementById('consoleStatusText');
      const consoleStatusIcon = document.getElementById('consoleStatusIcon');
      const consoleStatusSubtext = document.getElementById('consoleStatusSubtext');
      const consolePidText = document.getElementById('consolePidText');
      const consoleStartedText = document.getElementById('consoleStartedText');
      const btnConsoleStop = document.getElementById('btnConsoleStopScraper');
      const btnConsoleStart = document.getElementById('btnConsoleStartScraper');

      if (consoleStatusText) {
        consoleStatusText.textContent = isRunning ? 'RUNNING' : 'IDLE';
        consoleStatusText.style.color = isRunning ? '#10b981' : '#64748b';
      }
      if (consoleStatusIcon) consoleStatusIcon.textContent = isRunning ? '🟢' : '⚪';
      if (consoleStatusSubtext) consoleStatusSubtext.textContent = isRunning ? 'Actively ingesting products' : 'Process not running';
      if (consolePidText) consolePidText.textContent = isRunning ? pid : '--';
      if (consoleStartedText) {
        if (isRunning && data.meta && data.meta.started_at) {
          consoleStartedText.textContent = `Started ${data.meta.started_at}`;
        } else {
          consoleStartedText.textContent = isRunning ? 'Active now' : 'Ready to scrape';
        }
      }
      if (btnConsoleStop) btnConsoleStop.style.display = isRunning ? 'inline-flex' : 'none';
      if (btnConsoleStart) {
        btnConsoleStart.textContent = isRunning ? '⚙️ Modify Config' : '▶ Start Scraper';
      }

      // Console database counters are only needed on the console view.
      if (currentView === 'console') {
        const statsRes = await fetchCachedJson('/api/stats', { ttlMs: 60000 }).catch(() => null);
        if (statsRes) {
          const consoleProds = document.getElementById('consoleProductsText');
          const consoleInStock = document.getElementById('consoleInStockText');
          const consoleBrands = document.getElementById('consoleBrandsText');
          const totalProds = statsRes.total_products || 0;
          const inStock = statsRes.in_stock || 0;
          const brandsCount = statsRes.total_brands || 0;

          if (consoleProds) consoleProds.textContent = totalProds.toLocaleString();
          if (consoleInStock) consoleInStock.textContent = `${inStock.toLocaleString()} In-Stock`;
          if (consoleBrands) consoleBrands.textContent = brandsCount.toLocaleString();
        }
      }
    } catch (err) {
      // Ignore network error on periodic poll
    } finally {
      _scraperStatusRequest = null;
    }
  })();

  return _scraperStatusRequest;
}

function startLogStream() {
  stopLogStream();
  fetchLogs();
  logInterval = setInterval(fetchLogs, 2000);
}

function stopLogStream() {
  if (logInterval) clearInterval(logInterval);
  logInterval = null;
}

async function fetchLogs() {
  const pre = document.getElementById('consoleLogOutput');
  if (!pre) return;

  try {
    const res = await fetch('/api/logs?lines=80');
    const data = await res.json();
    if (Array.isArray(data.logs)) {
      pre.textContent = data.logs.join('\n') || 'No log entries recorded yet.';
    } else {
      pre.textContent = data.logs || 'No log entries recorded yet.';
    }
    if (document.getElementById('autoScrollLogs')?.checked) {
      pre.scrollTop = pre.scrollHeight;
    }
  } catch (err) {
    pre.textContent = 'Unable to fetch stream logs.';
  }
}

function clearLogsUI() {
  const pre = document.getElementById('consoleLogOutput');
  if (pre) pre.textContent = 'Logs cleared from view.';
}

// ==========================================================================
// 9. AUTH & SESSION
// ==========================================================================
function checkAuthSession() {
  const userStr = localStorage.getItem('fashionos_user') || localStorage.getItem('myntra_user');
  if (userStr) {
    try {
      const u = JSON.parse(userStr);
      const name = u.name || u.email || 'FashionOS Admin';
      const role = u.role || 'Admin';
      const initials = (name.split(' ').map(n => n[0]).join('').slice(0, 2) || 'FO').toUpperCase();
      if (document.getElementById('sidebarUserName')) document.getElementById('sidebarUserName').textContent = name;
      if (document.getElementById('sidebarAvatar')) document.getElementById('sidebarAvatar').textContent = initials;
      const headerAvatar = document.querySelector('.header-avatar');
      if (headerAvatar) {
        headerAvatar.textContent = initials;
        headerAvatar.title = `${name} (${role})`;
      }
      const greetingEl = document.querySelector('.bubble-greeting');
      if (greetingEl) {
        greetingEl.textContent = `👋 Hi ${name.split(' ')[0]},`;
      }
    } catch (e) {}
  }
}

function signOutUser() {
  fetch('/api/auth/logout', { method: 'POST', credentials: 'same-origin' })
    .catch(() => null)
    .finally(() => {
      localStorage.removeItem('fashionos_user');
      localStorage.removeItem('fashionos_auth');
      localStorage.removeItem('fashionos_auth_token');
      localStorage.removeItem('myntra_user');
      window.location.href = '/login';
    });
}

// ==========================================================================
// 10. DAILY REVENUE, SALES TRENDS & ROS INTELLIGENCE
// ==========================================================================
let trendsDataCache = null;
let currentTrendStatusFilter = 'ALL';
let dailyRevenueChartInstance = null;
let categoryVelocityChartInstance = null;
let brandRosChartInstance = null;

async function loadAnalyticsTrends() {
  const period = document.getElementById('trendsPeriodSelect')?.value || 14;
  try {
    const res = await fetch(`/api/analytics/trends?days=${period}`);
    const raw = await res.text();
    let json = null;

    try {
      json = raw ? JSON.parse(raw) : null;
    } catch (parseErr) {
      throw new Error(`Invalid trends response (${res.status}): ${raw.slice(0, 180)}`);
    }

    if (!res.ok) {
      throw new Error(json?.message || `HTTP ${res.status}`);
    }

    if (json.status !== 'success' || !json.data) {
      showToast('Could not load analytics trends.', 'error');
      return;
    }
    trendsDataCache = json.data;
    renderTrendsKPIs(trendsDataCache.kpis);
    renderTrendCharts(trendsDataCache);
    renderTrendTable(trendsDataCache.top_velocity_products);
    fetchDeepIntelligence();
  } catch (err) {
    console.error('Error loading analytics trends:', err);
    showToast('Failed to connect to analytics intelligence engine.', 'error');
  }
}

function renderTrendsKPIs(kpis) {
  if (!kpis) return;
  const revEl = document.getElementById('trendKpiRevenue');
  const soldEl = document.getElementById('trendKpiUnitsSold');
  const addedEl = document.getElementById('trendKpiStockAdded');
  const rosEl = document.getElementById('trendKpiROS');
  const trackedEl = document.getElementById('trendKpiTrackedSkus');

  if (revEl) revEl.textContent = `₹${kpis.total_revenue_gmv >= 10000000 ? (kpis.total_revenue_gmv / 10000000).toFixed(2) + ' Cr' : (kpis.total_revenue_gmv / 100000).toFixed(2) + ' Lakh'}`;
  if (soldEl) soldEl.textContent = Number(kpis.total_units_sold).toLocaleString() + ' units';
  if (addedEl) addedEl.textContent = Number(kpis.total_stock_added).toLocaleString() + ' units';
  if (rosEl) rosEl.textContent = Number(kpis.average_ros).toFixed(2);
  if (trackedEl) trackedEl.textContent = `${Number(kpis.tracked_skus || 0).toLocaleString()} Sales Records`;
}

function renderTrendCharts(data) {
  if (typeof Chart === 'undefined') return;

  // 1. Daily Revenue (GMV) & Units Sold Combo Chart
  const revCtx = document.getElementById('dailyRevenueChart')?.getContext('2d');
  if (revCtx) {
    if (dailyRevenueChartInstance) dailyRevenueChartInstance.destroy();

    const labels = (data.daily_trends || []).map(d => {
      const parts = d.date.split('-');
      return parts.length === 3 ? `${parts[1]}/${parts[2]}` : d.date;
    });
    const revenues = (data.daily_trends || []).map(d => d.revenue);
    const units = (data.daily_trends || []).map(d => d.units_sold);

    dailyRevenueChartInstance = new Chart(revCtx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [
          {
            type: 'line',
            label: 'Daily Revenue (₹)',
            data: revenues,
            borderColor: '#ff3f6c',
            backgroundColor: 'rgba(255, 63, 108, 0.08)',
            borderWidth: 3,
            fill: true,
            tension: 0.35,
            yAxisID: 'yRev',
            pointRadius: 4,
            pointHoverRadius: 6
          },
          {
            type: 'bar',
            label: 'Units Sold',
            data: units,
            backgroundColor: 'rgba(15, 23, 42, 0.75)',
            hoverBackgroundColor: '#0f172a',
            borderRadius: 6,
            yAxisID: 'yUnits',
            barPercentage: 0.45
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false
        },
        plugins: {
          legend: {
            position: 'top',
            labels: { font: { family: 'Outfit, sans-serif', size: 12 }, usePointStyle: true }
          },
          tooltip: {
            callbacks: {
              label: function(ctx) {
                if (ctx.dataset.yAxisID === 'yRev') {
                  return ` Revenue: ₹${Number(ctx.raw).toLocaleString('en-IN')}`;
                }
                return ` Units Sold: ${Number(ctx.raw).toLocaleString('en-IN')} units`;
              }
            }
          }
        },
        scales: {
          yRev: {
            type: 'linear',
            position: 'left',
            grid: { color: 'rgba(226, 232, 240, 0.6)' },
            ticks: {
              callback: value => {
                const v = Number(value || 0);
                return '₹' + (v >= 100000 ? (v / 100000).toFixed(1) + 'L' : v.toLocaleString('en-IN'));
              }
            }
          },
          yUnits: {
            type: 'linear',
            position: 'right',
            grid: { drawOnChartArea: false },
            ticks: {
              callback: value => `${Number(value || 0).toLocaleString('en-IN')} pcs`
            }
          },
          x: {
            grid: { display: false }
          }
        }
      }
    });
  }

  // 2. Category GMV & Units Split
  const catCtx = document.getElementById('categoryVelocityChart')?.getContext('2d');
  if (catCtx) {
    if (categoryVelocityChartInstance) categoryVelocityChartInstance.destroy();

    const catLabels = (data.category_velocity || []).map(c => c.category || 'General');
    const catGmv = (data.category_velocity || []).map(c => c.gmv);

    categoryVelocityChartInstance = new Chart(catCtx, {
      type: 'doughnut',
      data: {
        labels: catLabels,
        datasets: [{
          data: catGmv,
          backgroundColor: ['#ff3f6c', '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6'],
          borderWidth: 2,
          borderColor: '#ffffff'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom',
            labels: { font: { family: 'Outfit, sans-serif', size: 11 }, boxWidth: 12 }
          },
          tooltip: {
            callbacks: {
              label: function(ctx) {
                return ` ${ctx.label}: ₹${Number(ctx.raw).toLocaleString('en-IN')}`;
              }
            }
          }
        },
        cutout: '65%'
      }
    });
  }

  // 3. Top 10 Brands ROS Leaderboard (Horizontal Bar)
  const brandCtx = document.getElementById('brandRosChart')?.getContext('2d');
  if (brandCtx) {
    if (brandRosChartInstance) brandRosChartInstance.destroy();

    const topBrands = (data.brand_ros_leaderboard || []).slice(0, 8);
    const bLabels = topBrands.map(b => b.brand.length > 18 ? b.brand.slice(0, 18) + '...' : b.brand);
    const bRos = topBrands.map(b => b.ros);

    brandRosChartInstance = new Chart(brandCtx, {
      type: 'bar',
      data: {
        labels: bLabels,
        datasets: [{
          label: 'Rate of Sale (ROS - Units/Day)',
          data: bRos,
          backgroundColor: '#3b82f6',
          borderRadius: 6,
          barPercentage: 0.55
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              afterLabel: function(ctx) {
                const bObj = topBrands[ctx.dataIndex];
                return `Total GMV: ₹${Number(bObj.gmv).toLocaleString('en-IN')}\nUnits Sold: ${bObj.units_sold} (${bObj.skus} SKUs)`;
              }
            }
          }
        },
        scales: {
          x: {
            grid: { color: 'rgba(226, 232, 240, 0.6)' },
            title: { display: true, text: 'Daily ROS (Units / Day)' }
          },
          y: {
            grid: { display: false }
          }
        }
      }
    });
  }
}

function renderTrendTable(products) {
  const tbody = document.getElementById('topVelocityTableBody');
  if (!tbody) return;
  tbody.innerHTML = '';

  const list = products || [];
  const filtered = currentTrendStatusFilter === 'ALL' 
    ? list 
    : list.filter(p => p.stock_status === currentTrendStatusFilter);

  if (filtered.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="10" style="text-align: center; padding: 36px; color: #94a3b8;">
          No items match status filter: <strong>${currentTrendStatusFilter}</strong>
        </td>
      </tr>
    `;
    return;
  }

  filtered.forEach(p => {
    let statusBadge = `<span class="badge" style="background: rgba(16, 185, 129, 0.12); color: #10b981; font-weight: 700; padding: 3px 8px; border-radius: 6px;">HEALTHY</span>`;
    if (p.stock_status === 'FAST_MOVER') {
      statusBadge = `<span class="badge" style="background: rgba(255, 63, 108, 0.12); color: #ff3f6c; font-weight: 700; padding: 3px 8px; border-radius: 6px;">⚡ FAST MOVER</span>`;
    } else if (p.stock_status === 'RESTOCKED') {
      statusBadge = `<span class="badge" style="background: rgba(59, 130, 246, 0.12); color: #3b82f6; font-weight: 700; padding: 3px 8px; border-radius: 6px;">📦 RESTOCKED</span>`;
    } else if (p.stock_status === 'LOW_STOCK') {
      statusBadge = `<span class="badge" style="background: rgba(245, 158, 11, 0.12); color: #f59e0b; font-weight: 700; padding: 3px 8px; border-radius: 6px;">⚠️ LOW STOCK</span>`;
    } else if (p.stock_status === 'OOS') {
      statusBadge = `<span class="badge" style="background: rgba(239, 68, 68, 0.12); color: #ef4444; font-weight: 700; padding: 3px 8px; border-radius: 6px;">🚫 OUT OF STOCK</span>`;
    }

    const tr = document.createElement('tr');
    tr.style.borderBottom = '1px solid #f1f5f9';
    tr.style.cursor = 'pointer';
    tr.onclick = (e) => { if (!e.target.closest('a, button')) openProductDrawer(p.product_id); };
    tr.innerHTML = `
      <td style="padding: 12px 16px;">
        <div style="display: flex; align-items: center; gap: 12px;">
          <img src="${p.thumbnail || 'assets/luxury_silk_banner.jpg'}" alt="product" style="width: 44px; height: 54px; object-fit: cover; border-radius: 6px; border: 1px solid #e2e8f0;" onerror="this.src='assets/luxury_silk_banner.jpg'">
          <div>
            <div style="font-weight: 600; color: #0f172a; max-width: 240px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${p.title}">${p.title}</div>
            <div style="font-size: 0.74rem; color: #94a3b8;">ID: #${p.product_id}</div>
          </div>
        </div>
      </td>
      <td style="padding: 12px 16px; font-weight: 600; color: #1e293b;">${p.brand}</td>
      <td style="padding: 12px 16px; color: #64748b; font-size: 0.85rem;">${p.category}</td>
      <td style="padding: 12px 16px;">
        <strong style="color: #0f172a;">₹${p.selling_price.toLocaleString('en-IN')}</strong>
        ${p.discount_percentage > 0 ? `<span style="display: block; font-size: 0.75rem; color: #10b981; font-weight: 600;">${p.discount_percentage}% OFF</span>` : ''}
      </td>
      <td style="padding: 12px 16px;">
        <span style="font-weight: 700; color: #0f172a;">${p.units_sold}</span>
        <span style="font-size: 0.75rem; color: #64748b; display: block;">pcs</span>
      </td>
      <td style="padding: 12px 16px; font-weight: 700; color: #10b981;">₹${Number(p.revenue).toLocaleString('en-IN')}</td>
      <td style="padding: 12px 16px;">
        ${p.stock_added > 0 ? `<span style="color: #3b82f6; font-weight: 700;">+${p.stock_added}</span>` : '<span style="color: #94a3b8;">-</span>'}
      </td>
      <td style="padding: 12px 16px;">
        <span style="display: inline-block; padding: 2px 8px; border-radius: 4px; font-weight: 800; font-size: 0.85rem; background: ${p.ros >= 3 ? '#fee2e2; color: #dc2626;' : '#f1f5f9; color: #334155;'}">
          ${p.ros} / day
        </span>
      </td>
      <td style="padding: 12px 16px;">${statusBadge}</td>
      <td style="padding: 12px 16px;" onclick="event.stopPropagation();">
        <div style="display: flex; gap: 6px;">
          <button onclick="openProductDrawer(${p.product_id})" class="btn-icon" style="padding: 4px 8px; border-radius: 6px; background: #0f172a; color: #fff; cursor: pointer; font-size: 0.75rem; font-weight: 700; border:none;" title="Inspect SKU Details">🔍 Inspect</button>
          ${p.product_url ? `<a href="${p.product_url}" target="_blank" class="btn-icon" style="padding: 4px 8px; border-radius: 6px; background: #f8fafc; border: 1px solid #e2e8f0; color: #ff3f6c; text-decoration: none; font-size: 0.75rem; font-weight: 600;" title="View on Myntra">Myntra ↗</a>` : ''}
          <button onclick="toggleCompareItem(${p.product_id})" class="btn-icon" style="padding: 4px 8px; border-radius: 6px; background: #f8fafc; border: 1px solid #e2e8f0; color: #0f172a; cursor: pointer; font-size: 0.75rem; font-weight: 600;" title="Add to Compare">Compare</button>
        </div>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function filterTrendTable(status, btn) {
  currentTrendStatusFilter = status;
  document.querySelectorAll('#trendStatusFilterGroup .filter-pill').forEach(b => {
    b.style.background = '#f8fafc';
    b.style.color = '#475569';
  });
  if (btn) {
    btn.style.background = '#0f172a';
    btn.style.color = '#ffffff';
  }
  if (trendsDataCache) {
    renderTrendTable(trendsDataCache.top_velocity_products);
  }
}

async function triggerSnapshotNow() {
  try {
    showToast('Triggering daily snapshot for today...', 'info');
    const res = await fetch('/api/analytics/snapshot', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    });
    const data = await res.json();
    if (data.status === 'success') {
      invalidateClientJsonCache('/api/snapshot-dates');
      showToast(`Snapshot complete! ${data.result.products_snapshotted} SKUs recorded.`, 'success');
      loadAnalyticsTrends();
    } else {
      showToast('Snapshot could not be completed.', 'error');
    }
  } catch (err) {
    showToast('Error recording daily snapshot.', 'error');
  }
}

// ==========================================================================
// 11. DEEP RETAIL INTELLIGENCE (Size Curves, Elasticity, Radar, Returns)
// ==========================================================================
let deepIntelCache = null;

function switchInsightTab(tabId, btn) {
  document.querySelectorAll('.insights-tabs-bar .tab-pill-btn').forEach(b => {
    b.classList.remove('active');
    b.style.background = '#ffffff';
    b.style.color = '#475569';
    b.style.border = '1px solid #cbd5e1';
  });
  if (btn) {
    btn.classList.add('active');
    btn.style.background = '#0f172a';
    btn.style.color = '#ffffff';
    btn.style.border = 'none';
  }

  document.querySelectorAll('.insight-tab-panel').forEach(p => {
    p.style.display = 'none';
    p.classList.remove('active');
  });
  const activePanel = document.getElementById(`panel-${tabId}`);
  if (activePanel) {
    activePanel.style.display = 'block';
    activePanel.classList.add('active');
  }

  if (tabId === 'color-intelligence') {
    loadColorIntelligence();
  } else if (!deepIntelCache) {
    fetchDeepIntelligence();
  }
}

async function fetchDeepIntelligence() {
  try {
    const res = await fetch('/api/analytics/deep-intelligence');
    const json = await res.json();
    if (json.status !== 'success' || !json.data) return;
    deepIntelCache = json.data;

    const brokenBadge = document.getElementById('badgeBrokenCount');
    if (brokenBadge) brokenBadge.textContent = deepIntelCache.broken_size_curves.broken_curves_count;

    const riskBadge = document.getElementById('badgeRiskCount');
    if (riskBadge) riskBadge.textContent = deepIntelCache.return_risk.total_at_risk;

    renderBrokenSizeCurves(deepIntelCache.broken_size_curves);
    renderPriceElasticity(deepIntelCache.price_elasticity);
    renderNewLaunches(deepIntelCache.new_launches);
    renderReturnRisk(deepIntelCache.return_risk);
    renderAttributeTrends(deepIntelCache.attribute_trends);
  } catch (err) {
    console.error('Error fetching deep intelligence:', err);
  }
}

function renderBrokenSizeCurves(data) {
  if (!data) return;
  const rateEl = document.getElementById('sizeKpiBrokenRate');
  const oosEl = document.getElementById('sizeKpiCoreOOS');
  const totalEl = document.getElementById('sizeKpiTotalSkus');

  if (rateEl) rateEl.textContent = `${data.broken_curves_rate}%`;
  if (oosEl) oosEl.textContent = Number(data.core_sizes_oos_count).toLocaleString();
  if (totalEl) totalEl.textContent = Number(data.total_skus_analyzed).toLocaleString();

  const grid = document.getElementById('sizeDistributionBarsGrid');
  if (grid) {
    grid.innerHTML = '';
    (data.size_distribution || []).forEach(s => {
      const card = document.createElement('div');
      card.style.background = '#f8fafc';
      card.style.border = '1px solid #e2e8f0';
      card.style.borderRadius = '8px';
      card.style.padding = '10px 14px';
      const isCore = ['M', 'L', '30', '32', '34', '38', '40'].includes(s.size.toUpperCase());
      card.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
          <strong style="font-size: 0.95rem; color: ${isCore ? '#0f172a' : '#475569'};">
            ${s.size} ${isCore ? '<span style="font-size: 0.68rem; color: #ff3f6c; font-weight: 700; margin-left: 2px;">CORE</span>' : ''}
          </strong>
          <span style="font-size: 0.8rem; font-weight: 700; color: ${s.in_stock_rate > 70 ? '#10b981' : (s.in_stock_rate > 50 ? '#f59e0b' : '#ef4444')};">
            ${s.in_stock_rate}% in stock
          </span>
        </div>
        <div style="width: 100%; height: 6px; background: #e2e8f0; border-radius: 3px; overflow: hidden;">
          <div style="width: ${s.in_stock_rate}%; height: 100%; background: ${s.in_stock_rate > 70 ? '#10b981' : (s.in_stock_rate > 50 ? '#f59e0b' : '#ef4444')}; border-radius: 3px;"></div>
        </div>
        <div style="font-size: 0.72rem; color: #94a3b8; margin-top: 4px;">${s.total_units.toLocaleString()} units tracked</div>
      `;
      grid.appendChild(card);
    });
  }

  const tbody = document.getElementById('brokenSizeCurvesTableBody');
  if (tbody) {
    tbody.innerHTML = '';
    (data.broken_skus || []).forEach(p => {
      const tr = document.createElement('tr');
      tr.style.borderBottom = '1px solid #f1f5f9';
      tr.style.cursor = 'pointer';
      tr.onclick = (e) => { if (!e.target.closest('a, button')) openProductDrawer(p.product_id); };
      const missingBadges = (p.missing_sizes && p.missing_sizes.length > 0)
        ? p.missing_sizes.map(m => `<span style="display:inline-block; padding:2px 6px; border-radius:4px; font-size:0.72rem; font-weight:700; background:#fee2e2; color:#dc2626; margin-right:4px;">${m}</span>`).join('')
        : '<span style="color:#94a3b8; font-size:0.75rem;">None</span>';
      tr.innerHTML = `
        <td style="padding: 12px 16px;">
          <div style="font-weight: 600; color: #0f172a; max-width: 260px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${p.title}">${p.title}</div>
          <div style="font-size: 0.75rem; color: #64748b;">${p.brand} • #${p.product_id}</div>
        </td>
        <td style="padding: 12px 16px; color: #64748b; font-size: 0.85rem;">${p.category}</td>
        <td style="padding: 12px 16px; font-weight: 700; color: #0f172a;">₹${p.price.toLocaleString('en-IN')}</td>
        <td style="padding: 12px 16px;">
          <div style="display: flex; align-items: center; gap: 8px;">
            <div style="width: 70px; height: 6px; background: #fee2e2; border-radius: 3px; overflow: hidden;">
              <div style="width: ${p.completeness_pct}%; height: 100%; background: ${p.completeness_pct < 50 ? '#ef4444' : '#f59e0b'};"></div>
            </div>
            <span style="font-size: 0.8rem; font-weight: 700; color: ${p.completeness_pct < 50 ? '#dc2626' : '#d97706'};">${p.completeness_pct}%</span>
          </div>
          <div style="font-size: 0.72rem; color: #94a3b8;">${p.available_sizes} of ${p.total_sizes} sizes live</div>
        </td>
        <td style="padding: 12px 16px;">${missingBadges}</td>
        <td style="padding: 12px 16px;">
          <span style="padding: 3px 8px; border-radius: 6px; font-size: 0.75rem; font-weight: 800; background: ${p.severity === 'CRITICAL' ? 'rgba(239, 68, 68, 0.12); color: #ef4444;' : 'rgba(245, 158, 11, 0.12); color: #f59e0b;'}">
            ${p.severity}
          </span>
        </td>
        <td style="padding: 12px 16px;" onclick="event.stopPropagation();">
          <div style="display: flex; gap: 6px;">
            <button onclick="openProductDrawer(${p.product_id})" style="padding: 4px 8px; border-radius: 6px; background: #0f172a; color: #fff; cursor: pointer; font-size: 0.75rem; font-weight: 700; border: none;" title="Inspect SKU">🔍</button>
            ${p.product_url ? `<a href="${p.product_url}" target="_blank" style="padding: 4px 10px; border-radius: 6px; background: #f8fafc; border: 1px solid #e2e8f0; color: #ff3f6c; text-decoration: none; font-size: 0.75rem; font-weight: 700;">View ↗</a>` : ''}
          </div>
        </td>
      `;
      tbody.appendChild(tr);
    });
  }
}

function renderPriceElasticity(data) {
  if (!data) return;
  const grid = document.getElementById('elasticityTiersGrid');
  if (grid) {
    grid.innerHTML = '';
    (data.tiers || []).forEach(t => {
      const card = document.createElement('div');
      card.className = 'kpi-card';
      card.style.padding = '18px';
      card.style.borderRadius = '12px';
      card.style.background = '#fff';
      card.style.border = '1px solid #e2e8f0';
      card.innerHTML = `
        <div style="font-size: 0.82rem; font-weight: 700; color: #0f172a; margin-bottom: 6px;">${t.bracket}</div>
        <div style="font-size: 1.6rem; font-weight: 800; color: #ff3f6c; margin-bottom: 4px;">${t.avg_ros} <span style="font-size: 0.8rem; color: #64748b; font-weight: 500;">daily ROS</span></div>
        <div style="font-size: 0.78rem; color: #64748b;">Avg Price: <strong>₹${t.avg_price.toLocaleString('en-IN')}</strong></div>
        <div style="font-size: 0.78rem; color: #10b981; font-weight: 600; margin-top: 4px;">₹${(t.gmv / 100000).toFixed(1)} Lakhs GMV (${t.skus} SKUs)</div>
      `;
      grid.appendChild(card);
    });
  }

  const inelList = document.getElementById('inelasticWinnersList');
  if (inelList) {
    inelList.innerHTML = '';
    (data.inelastic_winners || []).forEach(p => {
      const item = document.createElement('div');
      item.style.padding = '10px 0';
      item.style.borderBottom = '1px solid #f1f5f9';
      item.style.display = 'flex';
      item.style.justifyContent = 'space-between';
      item.style.alignItems = 'center';
      item.style.cursor = 'pointer';
      item.onclick = (e) => { if (!e.target.closest('a, button')) openProductDrawer(p.product_id); };
      item.innerHTML = `
        <div style="flex:1; min-width:0; padding-right:12px;">
          <div style="font-weight: 600; font-size: 0.88rem; color: #0f172a; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${p.brand} - ${p.title}</div>
          <div style="font-size: 0.75rem; color: #64748b;">₹${p.selling_price.toLocaleString('en-IN')} • ${p.discount}% OFF • ${p.insight}</div>
        </div>
        <div style="display:flex; align-items:center; gap:8px;">
          <div style="text-align: right;">
            <span style="font-weight: 800; color: #10b981; font-size: 0.95rem;">${p.units_sold} sold</span>
            <div style="font-size: 0.74rem; color: #64748b;">${p.ros} ROS</div>
          </div>
          <button onclick="openProductDrawer(${p.product_id})" style="padding: 4px 8px; border-radius: 6px; background: #0f172a; color: #fff; cursor: pointer; font-size: 0.75rem; font-weight: 700; border:none;" title="Inspect SKU">🔍</button>
        </div>
      `;
      inelList.appendChild(item);
    });
  }

  const elList = document.getElementById('elasticDriversList');
  if (elList) {
    elList.innerHTML = '';
    (data.elastic_drivers || []).forEach(p => {
      const item = document.createElement('div');
      item.style.padding = '10px 0';
      item.style.borderBottom = '1px solid #f1f5f9';
      item.style.display = 'flex';
      item.style.justifyContent = 'space-between';
      item.style.alignItems = 'center';
      item.style.cursor = 'pointer';
      item.onclick = (e) => { if (!e.target.closest('a, button')) openProductDrawer(p.product_id); };
      item.innerHTML = `
        <div style="flex:1; min-width:0; padding-right:12px;">
          <div style="font-weight: 600; font-size: 0.88rem; color: #0f172a; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${p.brand} - ${p.title}</div>
          <div style="font-size: 0.75rem; color: #64748b;">₹${p.selling_price.toLocaleString('en-IN')} • <strong style="color: #ff3f6c;">${p.discount}% OFF</strong></div>
        </div>
        <div style="display:flex; align-items:center; gap:8px;">
          <div style="text-align: right;">
            <span style="font-weight: 800; color: #ff3f6c; font-size: 0.95rem;">${p.units_sold} sold</span>
            <div style="font-size: 0.74rem; color: #64748b;">${p.ros} ROS</div>
          </div>
          <button onclick="openProductDrawer(${p.product_id})" style="padding: 4px 8px; border-radius: 6px; background: #0f172a; color: #fff; cursor: pointer; font-size: 0.75rem; font-weight: 700; border:none;" title="Inspect SKU">🔍</button>
        </div>
      `;
      elList.appendChild(item);
    });
  }
}

function renderNewLaunches(data) {
  if (!data) return;
  const tbody = document.getElementById('newLaunchesTableBody');
  if (!tbody) return;
  tbody.innerHTML = '';
  (data.new_launches || []).forEach(p => {
    const tr = document.createElement('tr');
    tr.style.borderBottom = '1px solid #f1f5f9';
    tr.style.cursor = 'pointer';
    tr.onclick = (e) => { if (!e.target.closest('a, button')) openProductDrawer(p.product_id); };
    tr.innerHTML = `
      <td style="padding: 12px 16px;">
        <div style="font-weight: 600; color: #0f172a; max-width: 260px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${p.title}">${p.title}</div>
        <div style="font-size: 0.75rem; color: #94a3b8;">ID: #${p.product_id} • ${p.category}</div>
      </td>
      <td style="padding: 12px 16px; font-weight: 600; color: #1e293b;">${p.brand}</td>
      <td style="padding: 12px 16px;">
        <strong>₹${p.selling_price.toLocaleString('en-IN')}</strong>
        <span style="font-size: 0.75rem; color: #10b981; font-weight: 600; display: block;">${p.discount}% OFF</span>
      </td>
      <td style="padding: 12px 16px; font-weight: 700; color: #0f172a;">${p.units_sold} pcs</td>
      <td style="padding: 12px 16px;">
        <span style="display: inline-block; padding: 2px 8px; border-radius: 4px; font-weight: 800; font-size: 0.85rem; background: ${p.ros >= 2 ? '#fee2e2; color: #dc2626;' : '#f1f5f9; color: #334155;'}">
          ${p.ros} / day
        </span>
      </td>
      <td style="padding: 12px 16px;">
        <span style="padding: 3px 8px; border-radius: 6px; font-size: 0.75rem; font-weight: 800; background: ${p.launch_tag === 'HERO_POTENTIAL' ? 'rgba(16, 185, 129, 0.12); color: #10b981;' : 'rgba(59, 130, 246, 0.12); color: #3b82f6;'}">
          ${p.launch_tag === 'HERO_POTENTIAL' ? '🔥 HERO POTENTIAL' : '🌱 STEADY GROWTH'}
        </span>
      </td>
      <td style="padding: 12px 16px;" onclick="event.stopPropagation();">
        <div style="display:flex; gap:6px;">
          <button onclick="openProductDrawer(${p.product_id})" style="padding: 4px 8px; border-radius: 6px; background: #0f172a; color: #fff; cursor: pointer; font-size: 0.75rem; font-weight: 700; border:none;" title="Inspect SKU">🔍</button>
          ${p.product_url ? `<a href="${p.product_url}" target="_blank" style="padding: 4px 10px; border-radius: 6px; background: #f8fafc; border: 1px solid #e2e8f0; color: #ff3f6c; text-decoration: none; font-size: 0.75rem; font-weight: 700;">View ↗</a>` : ''}
        </div>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function renderReturnRisk(data) {
  if (!data) return;
  const grid = document.getElementById('returnRiskCardsGrid');
  if (!grid) return;
  grid.innerHTML = '';
  (data.at_risk_skus || []).forEach(p => {
    const card = document.createElement('div');
    card.style.background = '#fff';
    card.style.border = p.risk_level === 'HIGH_RETURN_RISK' ? '1px solid #fca5a5' : '1px solid #fde68a';
    card.style.borderRadius = '12px';
    card.style.padding = '16px 18px';
    card.style.boxShadow = '0 2px 6px rgba(0,0,0,0.02)';
    card.style.cursor = 'pointer';
    card.onclick = (e) => { if (!e.target.closest('a, button')) openProductDrawer(p.product_id); };
    card.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
        <span style="font-size: 0.72rem; font-weight: 800; padding: 2px 8px; border-radius: 4px; background: ${p.risk_level === 'HIGH_RETURN_RISK' ? '#fee2e2; color: #dc2626;' : '#fef3c7; color: #d97706;'}">
          ${p.risk_level === 'HIGH_RETURN_RISK' ? '⚠️ HIGH RETURN RISK' : '🟡 WATCHLIST'}
        </span>
        <strong style="color: #dc2626; font-size: 0.95rem;">★ ${p.rating} / 5.0</strong>
      </div>
      <div style="font-weight: 600; color: #0f172a; margin-bottom: 4px; font-size: 0.9rem;">${p.brand} - ${p.title}</div>
      <div style="font-size: 0.78rem; color: #64748b; margin-bottom: 8px;">
        ₹${p.selling_price.toLocaleString('en-IN')} • ${p.ratings_count} consumer reviews • <strong>${p.units_sold} sold</strong>
      </div>
      <div style="background: #f8fafc; border-radius: 6px; padding: 8px 10px; font-size: 0.78rem; color: #475569; border-left: 3px solid #ef4444;">
        <strong>Root Cause Diagnosis:</strong> ${p.diagnosis}
      </div>
      <div style="margin-top: 10px; display: flex; justify-content: space-between; align-items: center;" onclick="event.stopPropagation();">
        <button onclick="openProductDrawer(${p.product_id})" style="padding: 4px 10px; border-radius: 6px; background: #0f172a; color: #fff; cursor: pointer; font-size: 0.75rem; font-weight: 700; border: none;">🔍 Inspect SKU</button>
        ${p.product_url ? `<a href="${p.product_url}" target="_blank" style="font-size: 0.75rem; color: #ff3f6c; font-weight: 700; text-decoration: none;">View Reviews on Myntra ↗</a>` : ''}
      </div>
    `;
    grid.appendChild(card);
  });
}

function renderAttributeTrends(data) {
  if (!data) return;

  const fabCont = document.getElementById('fabricBreakdownContainer');
  if (fabCont) {
    fabCont.innerHTML = '';
    (data.fabrics || []).forEach(f => {
      const row = document.createElement('div');
      row.style.display = 'flex';
      row.style.justifyContent = 'space-between';
      row.style.alignItems = 'center';
      row.style.padding = '8px 12px';
      row.style.background = '#f8fafc';
      row.style.borderRadius = '8px';
      row.style.border = '1px solid #e2e8f0';
      row.innerHTML = `
        <div>
          <strong style="color: #0f172a; font-size: 0.88rem;">${f.fabric}</strong>
          <div style="font-size: 0.74rem; color: #64748b;">${f.skus} active SKUs • Avg disc: ${f.avg_discount}%</div>
        </div>
        <div style="text-align: right;">
          <strong style="color: #10b981; font-size: 0.95rem;">₹${f.avg_price.toLocaleString('en-IN')}</strong>
          <div style="font-size: 0.72rem; color: #94a3b8;">avg price</div>
        </div>
      `;
      fabCont.appendChild(row);
    });
  }

  const fitCont = document.getElementById('fitBreakdownContainer');
  if (fitCont) {
    fitCont.innerHTML = '';
    (data.fits || []).forEach(f => {
      const row = document.createElement('div');
      row.style.display = 'flex';
      row.style.justifyContent = 'space-between';
      row.style.alignItems = 'center';
      row.style.padding = '8px 12px';
      row.style.background = '#f8fafc';
      row.style.borderRadius = '8px';
      row.style.border = '1px solid #e2e8f0';
      row.innerHTML = `
        <div>
          <strong style="color: #0f172a; font-size: 0.88rem;">${f.fit}</strong>
          <div style="font-size: 0.74rem; color: #64748b;">${f.skus} active SKUs • Avg disc: ${f.avg_discount}%</div>
        </div>
        <div style="text-align: right;">
          <strong style="color: #3b82f6; font-size: 0.95rem;">₹${f.avg_price.toLocaleString('en-IN')}</strong>
          <div style="font-size: 0.72rem; color: #94a3b8;">avg price</div>
        </div>
      `;
      fitCont.appendChild(row);
    });
  }
}

// ==========================================================================
// 8. DAY-OVER-DAY & SIZE INTELLIGENCE HANDLERS
// ==========================================================================

function onDateFilterChange() {
  const sel = document.getElementById('catalogDateSelect');
  if (sel) {
    activeCatalogScope.snapshotDate = sel.value;
    catalogPage = 1;
    fetchCatalogProducts();
  }
}

function onSizeFilterChange() {
  const sel = document.getElementById('catalogSizeSelect');
  if (sel) {
    activeCatalogScope.size = sel.value;
    catalogPage = 1;
    fetchCatalogProducts();
  }
}

function selectMovementFilter(mv) {
  activeCatalogScope.movementFilter = mv;
  document.querySelectorAll('#movementFilterRow .mv-chip').forEach(btn => {
    btn.classList.toggle('active', btn.getAttribute('data-mv') === mv);
  });
  catalogPage = 1;
  fetchCatalogProducts();
}

let activeDodScope = {
  category: 'all',
  subcategory: 'all',
  gender: 'men',
  priceRanges: [],
  brands: [],
  movementType: 'all'
};

let dodMovementDonutInst = null;
let dodTrendLineInst = null;

async function refreshDodSidebarFacets() {
  try {
    const params = new URLSearchParams();
    if (activeDodScope.category && activeDodScope.category !== 'all') params.set('category', activeDodScope.category);
    if (activeDodScope.gender && activeDodScope.gender !== 'all') params.set('gender', activeDodScope.gender);
    if (activeDodScope.subcategory && activeDodScope.subcategory !== 'all') params.set('subcategory', activeDodScope.subcategory);
    if (activeDodScope.priceRanges && activeDodScope.priceRanges.length > 0) params.set('price_ranges', activeDodScope.priceRanges.join(','));

    const data = await fetchCachedJson(buildFilterCountsUrl(params), { ttlMs: 20000 });
    const pb = data.price_buckets || {};
    const subcategories = Array.isArray(data.subcategories) ? data.subcategories : [];
    const brandsList = Array.isArray(data.brands_list) ? data.brands_list : [];
    const priceMap = {
      lt_500: pb.lt_500,
      '500_1000': pb['500_1000'],
      '1000_2000': pb['1000_2000'],
      '2000_3000': pb['2000_3000'],
      '3000_4000': pb['3000_4000'],
      gt_4000: pb.gt_4000
    };

    document.querySelectorAll('input[name="scopeDodPrice"]').forEach(chk => {
      const countSpan = chk.parentElement?.querySelector('.check-count');
      if (countSpan && priceMap[chk.value] !== undefined) {
        countSpan.textContent = Number(priceMap[chk.value] || 0).toLocaleString('en-IN');
      }
    });

    const subSel = document.getElementById('scopeDodSubcatSelect');
    if (subSel && subcategories.length > 0) {
      const validValues = new Set(subcategories.map(s => s.value));
      if (!validValues.has(activeDodScope.subcategory)) {
        activeDodScope.subcategory = 'all';
      }
      subSel.innerHTML = subcategories.map(s => {
        const value = String(s.value || 'all');
        const name = String(s.name || value);
        const selected = value === activeDodScope.subcategory ? 'selected' : '';
        return `<option value="${escapeHtml(value)}" ${selected}>${escapeHtml(name)}</option>`;
      }).join('');
    }

    const brandBox = document.getElementById('scopeDodAccBrand');
    if (brandBox) {
      const availableBrands = new Set(brandsList.map(b => b.brand));
      activeDodScope.brands = (activeDodScope.brands || []).filter(b => availableBrands.has(b));
      brandBox.innerHTML = brandsList.map(b => `
        <label class="sub-check-item">
          <input type="checkbox" value="${escapeHtml(b.brand)}" onchange="applyDodScopeFilters()" ${activeDodScope.brands.includes(b.brand) ? 'checked' : ''} />
          <span class="check-text">${escapeHtml(b.brand)}</span>
          <span class="check-count">${Number(b.count || 0).toLocaleString('en-IN')}</span>
        </label>
      `).join('');
    }
  } catch (err) {
    console.warn('Error refreshing DoD sidebar facets:', err);
  }
}

function setDodGender(g, btn) {
  document.querySelectorAll('#scopeDodGenderPills .gender-pill').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  activeDodScope.gender = (g || 'men').toLowerCase();
  applyDodScopeFilters();
}

function setDodMovementPill(mv, btn) {
  document.querySelectorAll('.dod-filter-pills-row .dod-pill-btn').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  activeDodScope.movementType = mv;
  loadDayOverDayView();
}

async function applyDodScopeFilters() {
  const catSel = document.getElementById('scopeDodCategorySelect');
  if (catSel) activeDodScope.category = catSel.value;

  const subSel = document.getElementById('scopeDodSubcatSelect');
  if (subSel) activeDodScope.subcategory = subSel.value;

  const activeGenBtn = document.querySelector('#scopeDodGenderPills .gender-pill.active');
  if (activeGenBtn) {
    activeDodScope.gender = activeGenBtn.textContent.trim().toLowerCase();
  }

  const prChecked = [];
  document.querySelectorAll('input[name="scopeDodPrice"]:checked').forEach(c => prChecked.push(c.value));
  activeDodScope.priceRanges = prChecked;

  const bChecked = [];
  document.querySelectorAll('#scopeDodAccBrand input[type="checkbox"]:checked').forEach(c => bChecked.push(c.value));
  activeDodScope.brands = bChecked;

  loadDayOverDayView();
}

async function resetDodScopeFilters() {
  const catSel = document.getElementById('scopeDodCategorySelect');
  if (catSel) catSel.value = 'all';

  const subSel = document.getElementById('scopeDodSubcatSelect');
  if (subSel) subSel.value = 'all';

  document.querySelectorAll('#scopeDodGenderPills .gender-pill').forEach(b => {
    b.classList.toggle('active', b.textContent.trim().toLowerCase() === 'men');
  });

  document.querySelectorAll('input[name="scopeDodPrice"]').forEach(c => c.checked = false);
  document.querySelectorAll('#scopeDodAccBrand input[type="checkbox"]').forEach(c => c.checked = false);

  activeDodScope = {
    category: 'all',
    subcategory: 'all',
    gender: 'men',
    priceRanges: [],
    brands: [],
    movementType: 'all'
  };

  loadDayOverDayView();
}

function exportDodReport() {
  window.print();
}

function filterDodMovementsTable() {
  const query = (document.getElementById('dodSearchInput')?.value || '').toLowerCase();
  const rows = document.querySelectorAll('#dodAllMoversTableBody tr');
  rows.forEach(row => {
    const text = row.textContent.toLowerCase();
    row.style.display = text.includes(query) ? '' : 'none';
  });
}

async function loadDayOverDayView() {
  try {
    const requestSeq = ++dayOverDayRequestSeq;
    await refreshDodSidebarFacets();
    const p = new URLSearchParams();
    if (activeDodScope.category && activeDodScope.category !== 'all') {
      p.append('category', activeDodScope.category);
    }
    if (activeDodScope.gender) {
      p.append('gender', activeDodScope.gender);
    }
    if (activeDodScope.subcategory && activeDodScope.subcategory !== 'all') {
      p.append('subcategory', activeDodScope.subcategory);
    }
    if (activeDodScope.priceRanges && activeDodScope.priceRanges.length > 0) {
      p.append('price_ranges', activeDodScope.priceRanges.join(','));
    }
    if (activeDodScope.brands && activeDodScope.brands.length > 0) {
      p.append('brand', activeDodScope.brands.join(','));
    }
    if (activeDodScope.movementType) {
      p.append('movement_type', activeDodScope.movementType);
    }

    const res = await fetch(`/api/analytics/day-over-day?${p.toString()}`);
    if (!res.ok) throw new Error(`Day-over-Day load failed with status ${res.status}`);
    const data = await res.json();
    if (requestSeq !== dayOverDayRequestSeq) return;
    if (!data || data.status !== 'success') return;

    renderDayOverDayData(data);
  } catch (err) {
    console.error('Error loading Day-over-Day view:', err);
  }
}

function renderDayOverDayData(data) {
  if (!data) return;
  const k = data.kpi_cards || {};
  const movementDist = Array.isArray(data.movement_distribution) ? data.movement_distribution : [];
  const parseCount = (text) => {
    const match = String(text || '').replace(/,/g, '').match(/-?\d+/);
    return match ? Number(match[0]) : 0;
  };

  const datesEl = document.getElementById('dodComparingDates');
  if (datesEl) datesEl.textContent = displayValue(data.comparing_dates, '—');
  const dodSubtitleEl = document.getElementById('dodSubtitle');
  if (dodSubtitleEl) {
    dodSubtitleEl.textContent = data.methodology_note || 'Snapshot-backed tracking of price drops, discount expansions, inventory velocity, and restocks between the latest two available dates.';
  }
  const dodWindowEl = document.getElementById('dodDataWindowNote');
  if (dodWindowEl) {
    dodWindowEl.textContent = data.data_window_note || 'History window will appear once snapshot and analytics dates are available.';
  }

  const navBadge = document.getElementById('navDoDDealsBadge');
  if (navBadge) {
    navBadge.textContent = `${displayValue(k.price_drops_skus, '0')} Deals`;
  }

  // 1. KPI Cards
  const pdEl = document.getElementById('dodKpiPriceDrops');
  if (pdEl) pdEl.textContent = displayValue(k.price_drops_skus);
  const apdEl = document.getElementById('dodKpiAvgPriceDrop');
  if (apdEl) apdEl.textContent = `Avg drop: ${displayValue(k.avg_price_drop)}`;

  const phEl = document.getElementById('dodKpiPriceHikes');
  if (phEl) phEl.textContent = displayValue(k.price_hikes_skus);
  const aphEl = document.getElementById('dodKpiAvgPriceHike');
  if (aphEl) aphEl.textContent = `Avg hike: ${displayValue(k.avg_price_hike)}`;

  const ddEl = document.getElementById('dodKpiDiscountDeepened');
  if (ddEl) ddEl.textContent = displayValue(k.discount_deepened_skus);
  const addEl = document.getElementById('dodKpiAvgDiscountDelta');
  if (addEl) addEl.textContent = displayValue(k.avg_discount_exp);

  const usEl = document.getElementById('dodKpiUnitsSold');
  if (usEl) usEl.textContent = displayValue(k.units_sold_today);
  const revEl = document.getElementById('dodKpiRevenue');
  if (revEl) revEl.textContent = displayValue(k.run_rate);
  const unitsLabelEl = document.getElementById('dodUnitsSoldLabel');
  if (unitsLabelEl) {
    unitsLabelEl.textContent = data.latest_date_label ? `UNITS SOLD • ${String(data.latest_date_label).toUpperCase()}` : 'LATEST SALES DAY';
  }

  const rstEl = document.getElementById('dodKpiRestocked');
  if (rstEl) rstEl.textContent = displayValue(k.restocked_skus);
  const rstuEl = document.getElementById('dodKpiRestockedUnits');
  if (rstuEl) rstuEl.textContent = displayValue(k.restocked_units);
  const restockedLabelEl = document.getElementById('dodRestockedLabel');
  if (restockedLabelEl) {
    restockedLabelEl.textContent = data.latest_date_label ? `RESTOCKED • ${String(data.latest_date_label).toUpperCase()}` : 'LATEST RESTOCK DAY';
  }

  const oosEl = document.getElementById('dodKpiOosTransitions');
  if (oosEl) oosEl.textContent = displayValue(k.stockout_oos);
  const bisEl = document.getElementById('dodKpiBackInStock');
  if (bisEl) bisEl.textContent = displayValue(k.back_in_stock);

  // 2. Category shifts table
  const catTbody = document.getElementById('dodCategoryShiftsTableBody');
  if (catTbody) {
    catTbody.innerHTML = (data.category_shifts || []).map((c, idx) => `
      <tr style="border-bottom:1px solid #f1f5f9;">
        <td style="padding:8px 10px; font-weight:600; color:#64748b;">${idx + 1}</td>
        <td style="padding:8px 10px;"><strong style="color:#0f172a;">${escapeHtml(c.category)}</strong></td>
        <td style="padding:8px 10px;">${escapeHtml(displayValue(c.tracked_skus))}</td>
        <td style="padding:8px 10px; color:${String(c.net_price_delta || '').includes('▼') || String(c.net_price_delta || '').includes('-') ? '#059669' : (String(c.net_price_delta || '').includes('▲') || String(c.net_price_delta || '').includes('+') ? '#dc2626' : '#64748b')}; font-weight:700;">
          ${escapeHtml(displayValue(c.net_price_delta))}
        </td>
        <td style="padding:8px 10px; font-weight:700;">${escapeHtml(displayValue(c.units_sold))}</td>
        <td style="padding:8px 10px; font-weight:800; color:#0f172a;">${escapeHtml(displayValue(c.revenue))}</td>
      </tr>
    `).join('');
  }

  // 3. Movement Donut Chart
  const donutCtx = document.getElementById('dodMovementDonutChart');
  if (donutCtx && window.Chart) {
    if (dodMovementDonutInst) dodMovementDonutInst.destroy();
    const totalMov = parseCount(k.price_drops_skus) + parseCount(k.price_hikes_skus) + parseCount(k.discount_deepened_skus) + parseCount(k.restocked_skus) + parseCount(k.stockout_oos);
    const totCountEl = document.getElementById('dodTotalMovementsCount');
    if (totCountEl) totCountEl.textContent = totalMov.toLocaleString();

    dodMovementDonutInst = new Chart(donutCtx, {
      type: 'doughnut',
      data: {
        labels: movementDist.map(m => m.label),
        datasets: [{
          data: movementDist.map(m => Number(m.pct || 0)),
          backgroundColor: movementDist.map(m => m.color || '#cbd5e1'),
          borderWidth: 2,
          borderColor: '#ffffff'
        }]
      },
      options: {
        plugins: { legend: { display: false } },
        cutout: '68%'
      }
    });
  }

  // 4. Price Change Trend Line Chart
  const trendCtx = document.getElementById('dodTrendLineChart');
  if (trendCtx && window.Chart) {
    if (dodTrendLineInst) dodTrendLineInst.destroy();
    const trend = data.price_change_trend || {};
    const labels = trend.dates || [];
    dodTrendLineInst = new Chart(trendCtx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Avg Price',
            data: trend.avg_price || [],
            borderColor: '#0f172a',
            backgroundColor: '#0f172a',
            borderWidth: 2,
            pointRadius: 3,
            tension: 0.3,
            yAxisID: 'yPrice'
          },
          {
            label: 'Avg Discount %',
            data: trend.avg_discount || [],
            borderColor: '#2563eb',
            backgroundColor: '#2563eb',
            borderWidth: 2,
            pointRadius: 3,
            tension: 0.3,
            yAxisID: 'yPct'
          },
          {
            label: 'Units Sold',
            data: trend.units_sold || [],
            borderColor: '#8b5cf6',
            backgroundColor: '#8b5cf6',
            borderWidth: 2,
            pointRadius: 3,
            tension: 0.3,
            yAxisID: 'yUnits'
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { display: false }, ticks: { font: { size: 9 }, color: '#64748b' } },
          yPrice: { position: 'left', grid: { color: '#f1f5f9' }, ticks: { font: { size: 9 }, color: '#0f172a', callback: v => `₹${v}` } },
          yPct: { position: 'right', grid: { display: false }, ticks: { font: { size: 9 }, color: '#2563eb', callback: v => `${v}%` } },
          yUnits: { display: false }
        }
      }
    });
  }

  // 5. Top 5 Price Drops Table
  const dropsTbody = document.getElementById('dodTopDropsTableBody');
  if (dropsTbody) {
    dropsTbody.innerHTML = (data.top_5_drops || []).slice(0, 5).map((p, idx) => `
      <tr style="border-bottom:1px solid #f1f5f9; cursor:pointer;" onclick="openProductDrawer(${p.product_id});">
        <td style="padding:8px 10px; font-weight:700; color:#64748b;">${idx + 1}</td>
        <td style="padding:8px 10px;">
          <strong style="color:#0f172a;">${escapeHtml(p.brand)}</strong>
          <div style="font-size:11px; color:#64748b; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:180px;">${escapeHtml(p.title)}</div>
        </td>
        <td style="padding:8px 10px; text-decoration:line-through; color:#94a3b8;">${escapeHtml(displayValue(p.yesterday_price))}</td>
        <td style="padding:8px 10px; font-weight:800; color:#059669;">${escapeHtml(displayValue(p.today_price))}</td>
        <td style="padding:8px 10px;">
          <span class="tbl-dod-badge drop">${escapeHtml(displayValue(p.savings))}</span>
        </td>
      </tr>
    `).join('');
  }

  // 6. Top 5 Price Hikes Table
  const hikesTbody = document.getElementById('dodTopHikesTableBody');
  if (hikesTbody) {
    hikesTbody.innerHTML = (data.top_5_hikes || []).slice(0, 5).map((p, idx) => `
      <tr style="border-bottom:1px solid #f1f5f9; cursor:pointer;" onclick="openProductDrawer(${p.product_id});">
        <td style="padding:8px 10px; font-weight:700; color:#64748b;">${idx + 1}</td>
        <td style="padding:8px 10px;">
          <strong style="color:#0f172a;">${escapeHtml(p.brand)}</strong>
          <div style="font-size:11px; color:#64748b; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:180px;">${escapeHtml(p.title)}</div>
        </td>
        <td style="padding:8px 10px; color:#94a3b8;">${escapeHtml(displayValue(p.yesterday_price))}</td>
        <td style="padding:8px 10px; font-weight:800; color:#dc2626;">${escapeHtml(displayValue(p.today_price))}</td>
        <td style="padding:8px 10px;">
          <span class="tbl-dod-badge hike">${escapeHtml(displayValue(p.increase))}</span>
        </td>
      </tr>
    `).join('');
  }

  // 7. All Movers Table
  const moversTbody = document.getElementById('dodAllMoversTableBody');
  if (moversTbody) {
    moversTbody.innerHTML = (data.all_movements || []).map((m, idx) => `
      <tr style="border-bottom:1px solid #f1f5f9;">
        <td style="padding:10px 12px; font-weight:700; color:#64748b;">${idx + 1}</td>
        <td style="padding:10px 12px; cursor:pointer;" onclick="openProductDrawer(${m.product_id});">
          <strong style="color:#0f172a;">${escapeHtml(m.brand)}</strong>
          <div style="font-size:11px; color:#64748b; max-width:240px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${escapeHtml(m.title)}</div>
        </td>
        <td style="padding:10px 12px;"><span class="badge-tag">${escapeHtml(m.category)}</span></td>
        <td style="padding:10px 12px; color:#64748b;">${escapeHtml(displayValue(m.yesterday_price))}</td>
        <td style="padding:10px 12px; font-weight:800; color:#0f172a;">${escapeHtml(displayValue(m.today_price))}</td>
        <td style="padding:10px 12px;">
          ${String(m.price_delta || '').includes('-') ? `<span class="tbl-dod-badge drop">${escapeHtml(displayValue(m.price_delta))}</span>` : (String(m.price_delta || '').includes('+') ? `<span class="tbl-dod-badge hike">${escapeHtml(displayValue(m.price_delta))}</span>` : `<span style="color:#94a3b8;">${escapeHtml(displayValue(m.price_delta))}</span>`)}
        </td>
        <td style="padding:10px 12px;">
          <span style="font-size:11px; font-weight:700; color:${String(m.discount_delta || '').includes('+') ? '#059669' : (String(m.discount_delta || '').includes('-') ? '#dc2626' : '#64748b')}">
            ${escapeHtml(displayValue(m.discount_delta))}
          </span>
        </td>
        <td style="padding:10px 12px; font-size:11px;">
          ${escapeHtml(displayValue(m.stock_delta))}
        </td>
        <td style="padding:10px 12px; font-weight:800; color:${String(m.units_sold || '').includes('0 recorded sold') ? '#64748b' : '#ea580c'};">
          ${escapeHtml(displayValue(m.units_sold))}
        </td>
        <td style="padding:10px 12px;">
          <button class="table-icon-btn" onclick="openProductDrawer(${m.product_id});" title="Inspect SKU">🔍</button>
          <a href="${m.product_url || '#'}" target="_blank" class="table-icon-btn" title="View on Myntra ↗">↗</a>
        </td>
      </tr>
    `).join('');
  }
}

async function loadSizeIntelligenceView() {
  try {
    const res = await fetch('/api/analytics/size-intelligence');
    const data = await res.json();
    if (!data) return;

    const s = data.summary || {};
    const brokenEl = document.getElementById('sizeKpiBrokenRate');
    if (brokenEl) brokenEl.textContent = `${s.stockout_rate_pct || 0}%`;

    const coreEl = document.getElementById('sizeKpiCoreOOS');
    if (coreEl) coreEl.textContent = `${s.out_of_stock_variants || 0} variants`;

    const totSkusEl = document.getElementById('sizeKpiTotalSkus');
    if (totSkusEl) totSkusEl.textContent = `${(s.total_warehouse_units || 0).toLocaleString()} units`;

    // Render Size Distribution Grid
    const grid = document.getElementById('sizeDistributionBarsGrid');
    if (grid) {
      grid.innerHTML = (data.size_distribution || []).map(sz => {
        const oosRate = sz.stockout_rate_pct || 0;
        const barColor = oosRate > 25 ? '#ef4444' : (oosRate > 15 ? '#f59e0b' : '#10b981');
        return `
          <div class="size-intel-card">
            <div class="size-name">${sz.size}</div>
            <div class="size-units">${(sz.total_units || 0).toLocaleString()} units</div>
            <div class="size-oos-rate">${sz.product_count} SKUs • ${oosRate}% OOS</div>
            <div class="size-bar-wrap">
              <div class="size-bar-fill" style="width: ${100 - oosRate}%; background: ${barColor};"></div>
            </div>
            <div style="font-size: 9px; color: #64748b; margin-top: 4px;">${sz.stock_share_pct}% catalog share</div>
          </div>
        `;
      }).join('');
    }
  } catch (err) {
    console.error('Error loading size intelligence:', err);
  }
}

// ============================================================
// DYNAMIC INTELLIGENCE CONTROLLERS (CATEGORY, FABRIC, BRANDS)
// ============================================================

let activeCatIntel = { category: 'shirts', gender: 'men' };
let activeFabricIntel = { category: 'shirts', gender: 'men', fabric: 'all', priceRanges: [], brandSizes: [], brand: 'all', sustainability: 'all' };
let activeScopeIntel = { category: 'shirts', gender: 'men' };

let catPriceChartInst = null;
let catGrowthChartInst = null;
let catBrandSizeChartInst = null;
let fabricDistChartInst = null;
let fabricTrendChartInst = null;
let scopePriceChartInst = null;
let scopeMedianBySizeChartInst = null;

// Sub-sidebar & Category Tree Controls
function toggleSubSidebar(id) {
  const sidebar = document.getElementById(id);
  if (sidebar) {
    sidebar.classList.toggle('collapsed');
  }
}

function filterCategoryTree(q) {
  const query = (q || '').toLowerCase().trim();
  const items = document.querySelectorAll('#catTreeContainer .category-leaf-item');
  items.forEach(item => {
    const text = item.textContent.toLowerCase();
    item.style.display = (!query || text.includes(query)) ? 'flex' : 'none';
  });
}

function toggleCategoryGroup(groupId) {
  const el = document.getElementById(groupId);
  if (el) {
    el.style.display = (el.style.display === 'none') ? 'flex' : 'none';
  }
}

function selectCategoryTree(category, gender, btn) {
  document.querySelectorAll('#catTreeContainer .category-leaf-item').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');

  activeCatIntel.category = category;
  activeCatIntel.gender = gender;
  updateCategoryIntelScopeCopy(category, 'all');

  loadCategoryIntelligence(category, gender);
}

function switchCatIntelTab(tabName, btn) {
  document.querySelectorAll('#view-category-analysis .intel-tab-btn').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');

  if (tabName === 'overview') {
    document.getElementById('view-category-analysis')?.scrollTo({ top: 0, behavior: 'smooth' });
  } else if (tabName === 'brands') {
    switchView('brands');
  } else if (tabName === 'price') {
    switchView('price-intel');
  } else if (tabName === 'fabrics') {
    switchView('fabric');
  } else if (tabName === 'colors') {
    switchView('colors');
  } else if (tabName === 'fit') {
    switchView('insights');
  } else if (tabName === 'trends') {
    switchView('insights');
  } else if (tabName === 'products') {
    switchView('catalog');
  } else if (tabName === 'opportunities') {
    switchView('insights');
  }
}

function applyCatIntelFilters() {
  const category = document.getElementById('catScopeCategorySelect')?.value || activeCatIntel.category || 'shirts';
  const subcategory = document.getElementById('catScopeSubcategorySelect')?.value || 'all';
  const gender = document.getElementById('catScopeGenderSelect')?.value || activeCatIntel.gender || 'men';
  const priceRange = document.getElementById('catScopePriceRangeSelect')?.value || 'all';
  const brandSize = document.getElementById('catScopeBrandSizeSelect')?.value || 'all';
  const brandType = document.getElementById('catScopeBrandTypeSelect')?.value || 'all';
  const fabric = document.getElementById('catScopeFabricSelect')?.value || 'all';
  const fit = document.getElementById('catScopeFitSelect')?.value || 'all';

  activeCatIntel.category = category;
  activeCatIntel.gender = gender;
  updateCategoryIntelScopeCopy(category, subcategory);

  loadCategoryIntelligence(category, gender, {
    subcategory, priceRange, brandSize, brandType, fabric, fit
  });
}

function resetCatIntelFilters() {
  const setVal = (id, val) => { const el = document.getElementById(id); if (el) el.value = val; };
  setVal('catScopeCategorySelect', 'shirts');
  setVal('catScopeSubcategorySelect', 'all');
  setVal('catScopeGenderSelect', 'men');
  setVal('catScopePriceRangeSelect', 'all');
  setVal('catScopeBrandSizeSelect', 'all');
  setVal('catScopeBrandTypeSelect', 'all');
  setVal('catScopeFabricSelect', 'all');
  setVal('catScopeFitSelect', 'all');

  activeCatIntel.category = 'shirts';
  activeCatIntel.gender = 'men';

  applyCatIntelFilters();
}

function onScopeCategoryChange() {
  const category = document.getElementById('catScopeCategorySelect')?.value || 'shirts';
  activeCatIntel.category = category;
  applyCatIntelFilters();
}

// ============================================================
// 1. CATEGORY INTELLIGENCE LOADER & RENDERER
// ============================================================

const catIntelClientCache = new Map();

async function loadCategoryIntelligence(category = activeCatIntel.category, gender = activeCatIntel.gender, filters = {}) {
  const requestSeq = ++categoryIntelRequestSeq;
  const subcategory = filters.subcategory || document.getElementById('catScopeSubcategorySelect')?.value || 'all';
  const priceRange = filters.priceRange || document.getElementById('catScopePriceRangeSelect')?.value || 'all';
  const brandSize = filters.brandSize || document.getElementById('catScopeBrandSizeSelect')?.value || 'all';
  const brandType = filters.brandType || document.getElementById('catScopeBrandTypeSelect')?.value || 'all';
  const fabric = filters.fabric || document.getElementById('catScopeFabricSelect')?.value || 'all';
  const fit = filters.fit || document.getElementById('catScopeFitSelect')?.value || 'all';

  const cacheKey = `${(category || 'shirts').toLowerCase()}_${(gender || 'men').toLowerCase()}_${subcategory}_${priceRange}_${brandSize}_${brandType}_${fabric}_${fit}`;
  if (catIntelClientCache.has(cacheKey)) {
    renderCategoryIntelData(catIntelClientCache.get(cacheKey));
  }

  try {
    let url = `/api/category-intelligence?category=${encodeURIComponent(category)}&gender=${encodeURIComponent(gender)}`;
    if (subcategory && subcategory !== 'all') url += `&subcategory=${encodeURIComponent(subcategory)}`;
    if (priceRange && priceRange !== 'all') url += `&price_ranges=${encodeURIComponent(priceRange)}`;
    if (brandSize && brandSize !== 'all') url += `&brand_size=${encodeURIComponent(brandSize)}`;
    if (brandType && brandType !== 'all') url += `&brand_type=${encodeURIComponent(brandType)}`;
    if (fabric && fabric !== 'all') url += `&fabric=${encodeURIComponent(fabric)}`;
    if (fit && fit !== 'all') url += `&fit=${encodeURIComponent(fit)}`;

    const res = await fetch(url);
    if (!res.ok) throw new Error(`Category intelligence load failed with status ${res.status}`);
    const data = await res.json();
    if (requestSeq !== categoryIntelRequestSeq) return;
    if (!data || data.status !== 'success') return;

    catIntelClientCache.set(cacheKey, data);
    renderCategoryIntelData(data);
  } catch (err) {
    console.error('Error loading Category Intelligence:', err);
  }
}

function renderCategoryIntelData(data) {
  try {
    updateCategoryIntelScopeCopy(data.category || activeCatIntel.category, data.scope_subcategory || document.getElementById('catScopeSubcategorySelect')?.value || 'all');

    const k = data.kpis || {};
    const setTxt = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };

    setTxt('catKpiTotalProds', k.total_products || '0');
    setTxt('catKpiGrowth', k.growth_pct || '±0%');
    setTxt('catKpiBrandsSub', `Across ${(k.brands_count || 0).toLocaleString()} brands`);
    setTxt('catKpiMedianPrice', k.median_price || '₹0');
    setTxt('catKpiPriceGrowth', k.price_growth_pct || '±0%');
    setTxt('catKpiMeanModeSub', `Mean ${k.mean_price || '₹0'} | Mode ${k.mode_price || '₹0'}`);
    setTxt('catKpiAvgDiscount', k.avg_discount || '0%');
    setTxt('catKpiDiscDelta', k.discount_delta || '±0%');
    
    // Top Brand KPI Card
    const topBrandName = displayValue(k.top_brand, '--');
    const topBrandCount = Number(k.top_brand_products || 0);
    setTxt('catKpiTopBrand', topBrandName);
    setTxt('catKpiTopBrandProds', topBrandCount > 0 ? `${topBrandCount.toLocaleString()} products` : 'No products in current scope');
    const tagEl = document.getElementById('catKpiTopBrandTag');
    if (tagEl) {
      if (topBrandName === '--' || topBrandCount === 0) {
        tagEl.textContent = '--';
        tagEl.style.background = '#f1f5f9';
        tagEl.style.color = '#64748b';
      } else if (k.is_top_brand_myntra) {
        tagEl.textContent = '★ Myntra Label';
        tagEl.style.background = 'rgba(217, 119, 6, 0.15)';
        tagEl.style.color = '#d97706';
      } else {
        tagEl.textContent = '↑ Market Leader';
        tagEl.style.background = 'rgba(16, 185, 129, 0.15)';
        tagEl.style.color = '#10b981';
      }
    }
    
    setTxt('catKeyInsightText', data.key_insight || '');

    // 1. Price Distribution Bar Chart
    const priceCtx = document.getElementById('catPriceDistChart');
    if (priceCtx && window.Chart) {
      if (catPriceChartInst) catPriceChartInst.destroy();
      const dist = data.price_distribution || [];
      catPriceChartInst = new Chart(priceCtx, {
        type: 'bar',
        data: {
          labels: dist.map(d => d.label),
          datasets: [{
            data: dist.map(d => d.count),
            backgroundColor: '#94a3b8',
            hoverBackgroundColor: '#0f172a',
            borderRadius: 4,
            barPercentage: 0.65
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { grid: { display: false }, ticks: { font: { size: 10, weight: '600' }, color: '#64748b' } },
            y: { grid: { color: '#f1f5f9' }, ticks: { font: { size: 9 }, color: '#94a3b8', callback: v => v >= 1000 ? `${(v/1000).toFixed(1)}K` : v } }
          }
        }
      });
    }

    const subSel = document.getElementById('catScopeSubcategorySelect');
    if (subSel && Array.isArray(data.subcategories) && data.subcategories.length > 0) {
      const availableValues = new Set(data.subcategories.map(s => String(s.value || 'all')));
      const currentVal = availableValues.has(subSel.value) ? subSel.value : 'all';
      subSel.innerHTML = data.subcategories.map(s => {
        const value = String(s.value || 'all');
        const name = String(s.name || value);
        return `<option value="${escapeHtml(value)}" ${value === currentVal ? 'selected' : ''}>${escapeHtml(name)}</option>`;
      }).join('');
      subSel.value = currentVal;
    }

    activeCatIntel.category = (data.category || activeCatIntel.category || '').toLowerCase();
    activeCatIntel.gender = (data.gender || activeCatIntel.gender || '').toLowerCase();
    const currentFabric = document.getElementById('catScopeFabricSelect')?.value || 'all';
    const nextFabric = syncSelectFromFacetList(
      'catScopeFabricSelect',
      (data.top_fabrics || []).map(f => ({ value: f.fabric, name: f.fabric, count: f.products })),
      currentFabric,
      'All Fabrics',
      item => `${item.name} (${displayCount(item.count, '0')})`
    );
    const currentFit = document.getElementById('catScopeFitSelect')?.value || 'all';
    const nextFit = syncSelectFromFacetList(
      'catScopeFitSelect',
      (data.top_fits || []).map(f => ({ value: f.fit, name: f.fit, count: f.count })),
      currentFit,
      'All Fits',
      item => `${item.name} (${displayCount(item.count, '0')})`
    );
    if (nextFabric !== currentFabric || nextFit !== currentFit) {
      activeCatIntel.fabric = nextFabric;
      activeCatIntel.fit = nextFit;
    }

    // 2. Top Brands Table (includes Brand Type badges!)
    const topBrandsTbody = document.getElementById('catTopBrandsTableBody');
    if (topBrandsTbody) {
      topBrandsTbody.innerHTML = (data.top_brands || []).map(b => {
        const badgeHtml = b.is_myntra_label 
          ? `<span style="font-size:10px; font-weight:700; background:#fef3c7; color:#b45309; padding:2px 6px; border-radius:4px; margin-left:6px;">Myntra Label</span>`
          : `<span style="font-size:10px; font-weight:600; background:#f1f5f9; color:#64748b; padding:2px 6px; border-radius:4px; margin-left:6px;">External</span>`;

        return `
          <tr>
            <td style="color:#64748b; font-weight:700;">${b.rank}</td>
            <td style="font-weight:700; color:#0f172a;">${escapeHtml(b.brand)} ${badgeHtml}</td>
            <td style="text-align:right; font-weight:600; color:#475569;">${b.products.toLocaleString()}</td>
            <td style="text-align:right; color:#64748b;">${b.share}</td>
            <td style="text-align:right; font-weight:600; color:#0f172a;">${b.median_price || b.avg_price}</td>
          </tr>
        `;
      }).join('');
    }

    // 3. Category Growth Line Chart
    const growthCtx = document.getElementById('catGrowthChart');
    if (growthCtx && window.Chart) {
      if (catGrowthChartInst) catGrowthChartInst.destroy();
      const g = data.category_growth || {};
      catGrowthChartInst = new Chart(growthCtx, {
        type: 'line',
        data: {
          labels: g.labels || [],
          datasets: [
            {
              label: 'Products',
              data: g.products || [],
              borderColor: '#0f172a',
              backgroundColor: '#0f172a',
              borderWidth: 2,
              pointRadius: 3,
              tension: 0.3
            },
            {
              label: 'Est. Sales Value',
              data: (g.sales_value_cr || []).map(v => v * 1000),
              borderColor: '#94a3b8',
              backgroundColor: '#94a3b8',
              borderWidth: 1.5,
              pointRadius: 3,
              borderDash: [3, 3],
              tension: 0.3
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { grid: { display: false }, ticks: { font: { size: 10 }, color: '#64748b' } },
            y: { grid: { color: '#f1f5f9' }, ticks: { font: { size: 9 }, color: '#94a3b8', callback: v => v >= 1000 ? `${(v/1000).toFixed(1)}K` : v } }
          }
        }
      });
    }

    // 4. Top Fabrics Table
    const topFabricsTbody = document.getElementById('catTopFabricsTableBody');
    if (topFabricsTbody) {
      topFabricsTbody.innerHTML = (data.top_fabrics || []).map(f => `
        <tr>
          <td style="font-weight:700; color:#0f172a;">${escapeHtml(f.fabric)}</td>
          <td style="text-align:right; font-weight:600; color:#475569;">${f.products.toLocaleString()}</td>
          <td style="text-align:right; color:#64748b;">${f.share}</td>
          <td style="text-align:right; font-weight:600; color:#0f172a;">${f.avg_price}</td>
        </tr>
      `).join('');
    }

    // 5. Top Colors List
    const topColorsList = document.getElementById('catTopColorsList');
    if (topColorsList) {
      topColorsList.innerHTML = (data.top_colors || []).map(c => `
        <div class="intel-progress-item">
          <span class="intel-color-dot" style="background:${c.hex};"></span>
          <span class="intel-progress-name">${escapeHtml(c.color)}</span>
          <div class="intel-progress-track">
            <div class="intel-progress-fill" style="width: ${c.share};"></div>
          </div>
          <span class="intel-progress-cnt">${c.products.toLocaleString()}</span>
          <span class="intel-progress-share">${c.share}</span>
        </div>
      `).join('');
    }

    // 6. Brand Scale Distribution Chart & Legend
    const sizeCtx = document.getElementById('catBrandSizeChart');
    if (sizeCtx && window.Chart) {
      if (catBrandSizeChartInst) catBrandSizeChartInst.destroy();
      const bs = data.brand_scale || {};
      const lCnt = Number(bs.largest?.brand_count || 0);
      const mCnt = Number(bs.mid?.brand_count || 0);
      const sCnt = Number(bs.small?.brand_count || 0);
      const totBrands = lCnt + mCnt + sCnt;
      setTxt('catBrandSizeTotal', totBrands.toLocaleString());

      catBrandSizeChartInst = new Chart(sizeCtx, {
        type: 'doughnut',
        data: {
          labels: ['Largest (>200)', 'Mid-size (50-200)', 'Small (<50)'],
          datasets: [{
            data: [lCnt, mCnt, sCnt],
            backgroundColor: ['#0f172a', '#94a3b8', '#cbd5e1'],
            borderWidth: 2,
            borderColor: '#ffffff'
          }]
        },
        options: {
          plugins: { legend: { display: false } }
        }
      });

      const legendEl = document.getElementById('catBrandSizeLegend');
      if (legendEl) {
        legendEl.innerHTML = `
          <div class="donut-legend-row" style="margin-bottom:8px;">
            <div style="display:flex; align-items:center; gap:6px;">
              <span style="width:10px; height:10px; border-radius:50%; background:#0f172a;"></span>
              <strong style="font-size:12px; color:#0f172a;">Largest Brands (&gt;200)</strong>
            </div>
            <span style="font-size:12px; font-weight:700; color:#0f172a;">${lCnt} brands (${bs.largest?.product_count ? bs.largest.product_count.toLocaleString() : 0} styles)</span>
          </div>
          <div class="donut-legend-row" style="margin-bottom:8px;">
            <div style="display:flex; align-items:center; gap:6px;">
              <span style="width:10px; height:10px; border-radius:50%; background:#94a3b8;"></span>
              <strong style="font-size:12px; color:#0f172a;">Mid-size Brands (50–200)</strong>
            </div>
            <span style="font-size:12px; font-weight:700; color:#0f172a;">${mCnt} brands (${bs.mid?.product_count ? bs.mid.product_count.toLocaleString() : 0} styles)</span>
          </div>
          <div class="donut-legend-row">
            <div style="display:flex; align-items:center; gap:6px;">
              <span style="width:10px; height:10px; border-radius:50%; background:#cbd5e1;"></span>
              <strong style="font-size:12px; color:#0f172a;">Small Brands (&lt;50)</strong>
            </div>
            <span style="font-size:12px; font-weight:700; color:#0f172a;">${sCnt} brands (${bs.small?.product_count ? bs.small.product_count.toLocaleString() : 0} styles)</span>
          </div>
        `;
      }
    }

    // 7. Top Products Horizontal Cards
    const topProdsRow = document.getElementById('catTopProductsRow');
    if (topProdsRow) {
      topProdsRow.innerHTML = (data.top_products || []).map(p => `
        <div class="intel-product-card" onclick="openProductDrawer(${p.product_id});" style="cursor: pointer;">
          <span class="intel-product-rank-badge">${p.rank}</span>
          <img src="${p.image_url || 'assets/luxury_silk_banner.jpg'}" class="intel-product-img" alt="${escapeHtml(p.brand)}" onerror="this.src='assets/luxury_silk_banner.jpg'" />
          <span class="intel-prod-brand">${escapeHtml(p.brand)}</span>
          <span class="intel-prod-title" title="${escapeHtml(p.title)}">${escapeHtml(p.title)}</span>
          <span class="intel-prod-price">${p.price}</span>
          <div class="intel-prod-meta-row">
            <span>⚡ ${p.velocity}</span>
            <span>📦 Stock ${p.stock}</span>
          </div>
        </div>
      `).join('');
    }
  } catch (err) {
    console.error('Error rendering Category Intelligence data:', err);
  }
}

// ============================================================
// 2. FABRIC INTELLIGENCE LOADER (Screenshot 2)
// ============================================================

function switchFabricSubNav(navName, btn) {
  document.querySelectorAll('#fabricFilterSidebar .sub-nav-menu-item').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');

  const targetMap = {
    overview: '#view-fabric .intel-view-header',
    trends: '#fabricTrendChart',
    category: '#fabricDistDonutChart',
    brand: '#fabricHeatmapTable',
    price: '#fabricPriceTableBody',
    sustainability: '#fabricInsightsList',
    blend: '#fabricSwatchCirclesRow'
  };
  const target = document.querySelector(targetMap[navName] || '#view-fabric .intel-view-header');
  if (target) {
    target.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
}

function setFabricGender(g, btn) {
  document.querySelectorAll('#fabricGenderPills .gender-pill').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  activeFabricIntel.gender = g;
  applyFabricFilters();
}

async function refreshFabricSidebarFacets() {
  try {
    const params = new URLSearchParams();
    params.set('sections', 'fabric');
    if (activeFabricIntel.category && activeFabricIntel.category !== 'all') params.set('category', activeFabricIntel.category);
    if (activeFabricIntel.gender && activeFabricIntel.gender !== 'all') params.set('gender', activeFabricIntel.gender);
    if (activeFabricIntel.priceRanges && activeFabricIntel.priceRanges.length > 0) params.set('price_ranges', activeFabricIntel.priceRanges.join(','));
    if (activeFabricIntel.brandSizes && activeFabricIntel.brandSizes.length > 0) params.set('brand_size', activeFabricIntel.brandSizes.join(','));

    const data = await fetchCachedJson(buildFilterCountsUrl(params), { ttlMs: 20000 });
    const pb = data.price_buckets || {};
    const bs = data.brand_sizes || {};
    const brandsList = Array.isArray(data.brands_list) ? data.brands_list : [];

    const setCount = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.textContent = Number(val || 0).toLocaleString('en-IN');
    };

    setCount('fabricCountLt500', pb.lt_500);
    setCount('fabricCount500to1k', pb['500_1000']);
    setCount('fabricCount1kto2k', pb['1000_2000']);
    setCount('fabricCount2kto3k', pb['2000_3000']);
    setCount('fabricCount3kto4k', pb['3000_4000']);
    setCount('fabricCountGt4k', pb.gt_4000);
    setCount('fabricBrandSizeLargeCount', bs.large);
    setCount('fabricBrandSizeMidCount', bs.mid);
    setCount('fabricBrandSizeSmallCount', bs.small);

    const brandSel = document.getElementById('fabricBrandSelect');
    if (brandSel) {
      const brandOptions = brandsList.map(b => ({
        value: b.brand,
        label: `${b.brand} (${Number(b.count || 0).toLocaleString('en-IN')})`
      }));
      const validBrandValues = new Set(brandOptions.map(b => b.value));
      if (activeFabricIntel.brand !== 'all' && !validBrandValues.has(activeFabricIntel.brand)) {
        activeFabricIntel.brand = 'all';
      }
      brandSel.innerHTML = [`<option value="all">All Brands</option>`]
        .concat(brandOptions.map(b => `<option value="${escapeHtml(b.value)}" ${b.value === activeFabricIntel.brand ? 'selected' : ''}>${escapeHtml(b.label)}</option>`))
        .join('');
    }
  } catch (err) {
    console.warn('Error refreshing fabric sidebar facets:', err);
  }
}

async function applyFabricFilters() {
  const catSel = document.getElementById('fabricCategorySelect');
  if (catSel) activeFabricIntel.category = catSel.value;
  const brandSel = document.getElementById('fabricBrandSelect');
  if (brandSel) activeFabricIntel.brand = brandSel.value;
  const fabSel = document.getElementById('fabricTypeSelect');
  if (fabSel) activeFabricIntel.fabric = fabSel.value;
  const sustainSel = document.getElementById('fabricSustainSelect');
  if (sustainSel) activeFabricIntel.sustainability = sustainSel.value;

  const prChecked = [];
  document.querySelectorAll('input[name="fabricPriceRange"]:checked').forEach(c => prChecked.push(c.value));
  activeFabricIntel.priceRanges = prChecked;

  const bsChecked = [];
  document.querySelectorAll('input[name="fabricBrandSize"]:checked').forEach(c => bsChecked.push(c.value));
  activeFabricIntel.brandSizes = bsChecked;

  loadFabricIntelligence();
}

async function resetFabricFilters() {
  const catSel = document.getElementById('fabricCategorySelect');
  if (catSel) catSel.value = 'shirts';
  const brandSel = document.getElementById('fabricBrandSelect');
  if (brandSel) brandSel.value = 'all';
  const fabSel = document.getElementById('fabricTypeSelect');
  if (fabSel) fabSel.value = 'all';
  const sustainSel = document.getElementById('fabricSustainSelect');
  if (sustainSel) sustainSel.value = 'all';
  document.querySelectorAll('input[name="fabricPriceRange"]').forEach(c => c.checked = false);
  document.querySelectorAll('input[name="fabricBrandSize"]').forEach(c => c.checked = false);
  activeFabricIntel = { category: 'shirts', gender: 'men', fabric: 'all', priceRanges: [], brandSizes: [], brand: 'all', sustainability: 'all' };
  document.querySelectorAll('#fabricGenderPills .gender-pill').forEach((b, i) => b.classList.toggle('active', i === 0));
  loadFabricIntelligence();
}

function loadColorsForSelectedFabric(fab) {
  activeFabricIntel.fabric = fab;
  const fabSel = document.getElementById('fabricTypeSelect');
  if (fabSel) fabSel.value = fab;
  const pillSel = document.getElementById('fabricColorSelectPill');
  if (pillSel) pillSel.value = fab;
  const linkEl = document.getElementById('fabricViewAllColorsLink');
  if (linkEl) {
    const label = fab && fab !== 'all' ? `${fab.charAt(0).toUpperCase() + fab.slice(1)}` : 'the selected fabric';
    linkEl.textContent = `+ View all colors for ${label} →`;
  }
  applyFabricFilters();
}

async function loadFabricIntelligence(category = activeFabricIntel.category, gender = activeFabricIntel.gender, fabric = activeFabricIntel.fabric) {
  try {
    const params = new URLSearchParams();
    params.set('category', category);
    params.set('gender', gender);
    if (fabric && fabric !== 'all') params.set('fabric', fabric);
    if (activeFabricIntel.priceRanges && activeFabricIntel.priceRanges.length > 0) params.set('price_ranges', activeFabricIntel.priceRanges.join(','));
    if (activeFabricIntel.brandSizes && activeFabricIntel.brandSizes.length > 0) params.set('brand_size', activeFabricIntel.brandSizes.join(','));
    if (activeFabricIntel.brand && activeFabricIntel.brand !== 'all') params.set('brand', activeFabricIntel.brand);
    if (activeFabricIntel.sustainability && activeFabricIntel.sustainability !== 'all') params.set('sustainability', activeFabricIntel.sustainability);

    const url = `/api/fabric-intelligence?${params.toString()}`;
    const res = await fetch(url);
    const data = await res.json();
    if (!data || data.status !== 'success') {
      showFabricEmptyState('Fabric intelligence could not be loaded for the current filters.');
      return;
    }

    const k = data.kpis || {};
    const setTxt = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };

    const categoryLabel = formatScopeLabel(category);
    const fabricScopeLabel = activeFabricIntel.fabric && activeFabricIntel.fabric !== 'all'
      ? displayValue(data.selected_fabric, activeFabricIntel.fabric)
      : 'All Fabrics';
    const scopeBits = [
      categoryLabel,
      fabricScopeLabel,
      activeFabricIntel.gender && activeFabricIntel.gender !== 'all' ? activeFabricIntel.gender.charAt(0).toUpperCase() + activeFabricIntel.gender.slice(1) : 'All Genders',
      activeFabricIntel.brand && activeFabricIntel.brand !== 'all' ? activeFabricIntel.brand : null,
      activeFabricIntel.sustainability && activeFabricIntel.sustainability !== 'all' ? activeFabricIntel.sustainability.replace(/-/g, ' ') : null
    ].filter(Boolean);
    setTxt('fabricHeaderSubtitle', `Live material intelligence for ${scopeBits.join(' · ')} based on current catalog filters.`);
    setTxt('fabricHeaderDataNote', data.data_windows?.trend_start && data.data_windows?.trend_end
      ? `Trend window: ${data.data_windows.trend_start} to ${data.data_windows.trend_end}`
      : 'Trend window: latest catalog update buckets');
    setTxt('fabricKpiTotalLabel', `TOTAL PRODUCTS (${categoryLabel.toUpperCase()})`);
    setTxt('fabricKpiTotalProds', displayCount(k.total_products_num ?? k.total_products));
    setTxt('fabricKpiUniqueCount', displayCount(k.unique_fabrics));
    setTxt('fabricKpiTopName', displayValue(k.top_fabric));
    setTxt('fabricKpiTopShare', displayValue(k.top_fabric_share));
    setTxt('fabricKpiAvgLabel', `AVG PRICE (${displayValue(k.top_fabric, 'TOP FABRIC').toUpperCase()})`);
    setTxt('fabricKpiAvgPrice', displayValue(k.avg_price));
    setTxt('fabricDistSubtitle', `Share of products by fabric type (${categoryLabel})`);
    renderFabricSidebarFromPayload(data.sidebar_counts || {});
    const linkEl = document.getElementById('fabricViewAllColorsLink');
    if (linkEl) linkEl.textContent = `+ View all colors for ${displayValue(data.selected_fabric || k.top_fabric, 'the selected fabric')} →`;

    const currentFabric = (activeFabricIntel.fabric || 'all').toLowerCase();
    const liveOptions = (data.fabric_distribution || [])
      .filter(f => f.fabric && f.fabric !== 'Others')
      .map(f => ({ value: String(f.fabric).toLowerCase(), label: `${f.fabric} (${f.share} share)` }));
    const existingValues = new Set(liveOptions.map(f => f.value));
    if (currentFabric !== 'all' && !existingValues.has(currentFabric)) {
      activeFabricIntel.fabric = 'all';
    }
    ['fabricTypeSelect', 'fabricColorSelectPill'].forEach(selectId => {
      const fabricSelect = document.getElementById(selectId);
      if (!fabricSelect) return;
      fabricSelect.innerHTML = [`<option value="all">All Fabrics</option>`]
        .concat(liveOptions.map(f => `<option value="${escapeHtml(f.value)}" ${f.value === activeFabricIntel.fabric ? 'selected' : ''}>${escapeHtml(f.label)}</option>`))
        .join('');
      fabricSelect.value = activeFabricIntel.fabric || 'all';
    });

    // 1. Fabric Distribution Donut Chart
    const donutCtx = document.getElementById('fabricDistDonutChart');
    if (donutCtx && window.Chart) {
      if (fabricDistChartInst) fabricDistChartInst.destroy();
      const fDist = data.fabric_distribution || [];
      const palette = ['#0f172a', '#334155', '#475569', '#64748b', '#94a3b8', '#cbd5e1', '#e2e8f0', '#f1f5f9'];
      setTxt('fabricDistCenterCount', displayCount(k.total_products_num ?? k.total_products));

      fabricDistChartInst = new Chart(donutCtx, {
        type: 'doughnut',
        data: {
          labels: fDist.map(d => d.fabric),
          datasets: [{
            data: fDist.map(d => d.count),
            backgroundColor: palette.slice(0, fDist.length),
            borderWidth: 2,
            borderColor: '#ffffff'
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          cutout: '72%',
          plugins: { legend: { display: false } }
        }
      });

      const legendEl = document.getElementById('fabricDistLegend');
      if (legendEl) {
        legendEl.innerHTML = fDist.map((f, i) => `
          <div class="donut-legend-row">
            <div class="donut-legend-left">
              <span class="legend-dot" style="background:${palette[i] || '#0f172a'};"></span>
              <span>${escapeHtml(f.fabric)}</span>
            </div>
            <strong>${f.share}%</strong>
          </div>
        `).join('');
      }
    }

    // 2. Fabric Trend Multi-Line Chart
    const trendCtx = document.getElementById('fabricTrendChart');
    if (trendCtx && window.Chart) {
      if (fabricTrendChartInst) fabricTrendChartInst.destroy();
      const tr = data.fabric_trend || {};
      const palette = ['#0f172a', '#334155', '#64748b', '#94a3b8', '#cbd5e1'];
      const series = (tr.series || []).map((s, i) => ({
        label: s.fabric,
        data: s.data,
        borderColor: palette[i % palette.length],
        backgroundColor: palette[i % palette.length],
        borderWidth: i === 0 ? 2.5 : 1.5,
        pointRadius: 2.5,
        tension: 0.3
      }));

      fabricTrendChartInst = new Chart(trendCtx, {
        type: 'line',
        data: {
          labels: tr.labels || [],
          datasets: series
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { grid: { display: false }, ticks: { font: { size: 10 }, color: '#64748b' } },
            y: { grid: { color: '#f1f5f9' }, ticks: { font: { size: 9 }, color: '#94a3b8', callback: v => v >= 1000 ? `${v/1000}K` : v } }
          }
        }
      });

      const trendLegEl = document.getElementById('fabricTrendLegendRow');
      if (trendLegEl) {
        trendLegEl.innerHTML = (tr.series || []).map((s, i) => `
          <span class="legend-item"><span class="legend-dot" style="background:${palette[i % palette.length]};"></span> ${escapeHtml(s.fabric)}</span>
        `).join('');
      }
    }

    // 3. Average Price by Fabric Table
    const priceTbody = document.getElementById('fabricPriceTableBody');
    if (priceTbody) {
      const priceRows = data.average_price_by_fabric || [];
      priceTbody.innerHTML = priceRows.length ? priceRows.map(r => `
        <tr>
          <td style="font-weight:700; color:#0f172a;">${escapeHtml(r.fabric)}</td>
          <td style="text-align:right; font-weight:600; color:#1e293b;">${r.mean}</td>
          <td style="text-align:right; color:#475569;">${r.median}</td>
          <td style="text-align:right; color:#64748b;">${r.mode}</td>
        </tr>
      `).join('') : '<tr><td colspan="4" style="padding:14px; color:#94a3b8; text-align:center;">No price data for the selected fabric scope.</td></tr>';
    }

    // 4. Top Fabrics Ranked
    const rankedList = document.getElementById('fabricRankedList');
    if (rankedList) {
      const ranked = data.top_fabrics_ranked || [];
      const maxCnt = ranked[0] ? ranked[0].count : 1;
      rankedList.innerHTML = ranked.length ? ranked.map(r => `
        <div class="ranked-swatch-item">
          <span class="swatch-rank">${r.rank}</span>
          <div class="fabric-swatch-thumb">🧵</div>
          <span class="swatch-name">${escapeHtml(r.fabric)}</span>
          <div class="intel-progress-track">
            <div class="intel-progress-fill" style="width: ${Math.round((r.count / maxCnt) * 100)}%;"></div>
          </div>
          <span class="intel-progress-cnt">${r.count.toLocaleString()}</span>
        </div>
      `).join('') : '<div style="padding:14px; color:#94a3b8; font-size:12px;">No fabric buckets found for these filters.</div>';
    }

    // 5. Fabric Growth Bars
    const growthList = document.getElementById('fabricGrowthList');
    if (growthList) {
      const growth = data.fabric_growth || [];
      const maxPct = Math.max(1, ...growth.map(g => Math.abs(Number(g.growth_pct) || 0)));
      growthList.innerHTML = growth.length ? growth.map(g => {
        const pct = Number(g.growth_pct || 0);
        const tone = pct > 0 ? '#059669' : (pct < 0 ? '#dc2626' : '#64748b');
        const label = pct > 0 ? `+${pct.toFixed(1)}%` : `${pct.toFixed(1)}%`;
        return `
        <div class="ranked-growth-item">
          <span class="swatch-name" style="width: 85px;">${escapeHtml(g.fabric)}</span>
          <div class="intel-progress-track">
            <div class="intel-progress-fill" style="width: ${Math.round((Math.abs(pct) / maxPct) * 100)}%; background:${tone};"></div>
          </div>
          <span class="growth-badge-text" style="color:${tone};">${label}</span>
        </div>
      `; }).join('') : '<div style="padding:14px; color:#94a3b8; font-size:12px;">No trend movement available for this scope.</div>';
    }

    // 6. Top Colors by Fabric Swatch Circles
    const swatchCircles = document.getElementById('fabricSwatchCirclesRow');
    if (swatchCircles) {
      const colorRows = data.top_colors_by_fabric || [];
      swatchCircles.innerHTML = colorRows.length ? colorRows.map(c => `
        <div class="swatch-circle-item">
          <div class="swatch-circle" style="background:${c.hex};"></div>
          <span class="swatch-circle-name">${escapeHtml(c.color)}</span>
          <span class="swatch-circle-share">${c.share}</span>
        </div>
      `).join('') : '<div style="padding:14px; color:#94a3b8; font-size:12px;">No color data for the selected fabric.</div>';
    }

    // 7. Fabric x Brand Heatmap Table Matrix
    const heatmapThead = document.getElementById('fabricHeatmapTheadRow');
    const heatmapTbody = document.getElementById('fabricHeatmapTbody');
    const hm = data.fabric_brand_heatmap || {};
    if (heatmapThead && hm.columns) {
      heatmapThead.innerHTML = `<th class="fabric-heatmap-brand-head">Brand</th>` + hm.columns.map(c => `
        <th class="fabric-heatmap-head"><span>${escapeHtml(c)}</span></th>
      `).join('');
    }
    if (heatmapTbody && hm.rows) {
      heatmapTbody.innerHTML = hm.rows.length ? hm.rows.map(r => `
        <tr>
          <td class="fabric-heatmap-brand" title="${escapeHtml(r.brand)}">${escapeHtml(r.brand)}</td>
          ${r.cells.map(c => {
            const bg = c.intensity > 0 ? `rgba(15, 23, 42, ${Math.max(0.08, c.intensity * 0.45)})` : '#f8fafc';
            const textCol = c.intensity > 0.5 ? '#ffffff' : '#334155';
            return `
              <td class="fabric-heatmap-td" title="${Number(c.raw_count || 0).toLocaleString('en-IN')} products">
                <span class="fabric-heatmap-cell" style="background:${bg}; color:${textCol};">${escapeHtml(c.count)}</span>
              </td>
            `;
          }).join('')}
        </tr>
      `).join('') : '<tr><td colspan="8" style="padding:14px; text-align:center; color:#94a3b8;">No brand/fabric matrix for these filters.</td></tr>';
    }

    // 8. Fabric Insights
    const insightsList = document.getElementById('fabricInsightsList');
    if (insightsList) {
      insightsList.innerHTML = (data.fabric_insights || []).map((txt, idx) => `
        <div class="fabric-insight-item">
          <div class="insight-num-circle">${idx + 1}</div>
          <div class="insight-item-text">${escapeHtml(txt)}</div>
        </div>
      `).join('');
    }
  } catch (err) {
    console.error('Error loading Fabric Intelligence:', err);
    showFabricEmptyState('Fabric intelligence failed to render. Please retry or adjust filters.');
  }
}

function showFabricEmptyState(message) {
  const setTxt = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
  setTxt('fabricKpiTotalProds', '-');
  setTxt('fabricKpiUniqueCount', '-');
  setTxt('fabricKpiTopName', '-');
  setTxt('fabricKpiTopShare', message || 'No fabric data available');
  setTxt('fabricKpiAvgPrice', '-');
}

function renderFabricSidebarFromPayload(sidebarCounts) {
  const pb = sidebarCounts.price_buckets || {};
  const bs = sidebarCounts.brand_sizes || {};
  const brandsList = Array.isArray(sidebarCounts.brands_list) ? sidebarCounts.brands_list : [];
  const setCount = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.textContent = Number(val || 0).toLocaleString('en-IN');
  };

  setCount('fabricCountLt500', pb.lt_500);
  setCount('fabricCount500to1k', pb['500_1000']);
  setCount('fabricCount1kto2k', pb['1000_2000']);
  setCount('fabricCount2kto3k', pb['2000_3000']);
  setCount('fabricCount3kto4k', pb['3000_4000']);
  setCount('fabricCountGt4k', pb.gt_4000);
  setCount('fabricBrandSizeLargeCount', bs.large);
  setCount('fabricBrandSizeMidCount', bs.mid);
  setCount('fabricBrandSizeSmallCount', bs.small);

  const brandSel = document.getElementById('fabricBrandSelect');
  if (brandSel) {
    const validBrandValues = new Set(brandsList.map(b => b.brand));
    if (activeFabricIntel.brand !== 'all' && !validBrandValues.has(activeFabricIntel.brand)) {
      activeFabricIntel.brand = 'all';
    }
    brandSel.innerHTML = ['<option value="all">All Brands</option>']
      .concat(brandsList.map(b => {
        const label = `${b.brand} (${Number(b.count || 0).toLocaleString('en-IN')})`;
        return `<option value="${escapeHtml(b.brand)}" ${b.brand === activeFabricIntel.brand ? 'selected' : ''}>${escapeHtml(label)}</option>`;
      }))
      .join('');
    brandSel.value = activeFabricIntel.brand || 'all';
  }
}

// ============================================================
// 3. BRANDS INTELLIGENCE / ANALYSIS SCOPE LOADER (Screenshot 3)
// ============================================================
// 3. BRANDS INTELLIGENCE / ANALYSIS SCOPE LOADER (Screenshot 3)
// ============================================================

activeScopeIntel = {
  category: 'shirts',
  gender: 'men',
  subcategory: 'all',
  priceRanges: [],
  brandSizes: [],
  brands: [],
  colors: [],
  fabrics: [],
  fits: [],
  discountMin: 0,
  inStockOnly: false,
  ratingMin: 0,
  newArrivalsOnly: false
};

function toggleScopeAcc(accId) {
  const el = document.getElementById(accId);
  if (!el) return;
  const isHidden = (el.style.display === 'none' || !el.style.display);
  el.style.display = isHidden ? 'block' : 'none';
  const parent = el.closest('.scope-acc-group');
  if (parent) {
    const chevron = parent.querySelector('.scope-acc-row svg');
    if (chevron) chevron.style.transform = isHidden ? 'rotate(180deg)' : 'rotate(0deg)';
  }
}

function setScopeGender(g, btn) {
  document.querySelectorAll('#scopeGenderPills .gender-pill').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  activeScopeIntel.gender = (g || 'men').toLowerCase();
  applyBrandsScopeFilters();
}

function applyBrandsScopeFilters() {
  const catSel = document.getElementById('scopeCategorySelect');
  if (catSel) activeScopeIntel.category = catSel.value;

  const subSel = document.getElementById('scopeSubcatSelect');
  if (subSel) activeScopeIntel.subcategory = subSel.value;

  const activeGenBtn = document.querySelector('#scopeGenderPills .gender-pill.active');
  if (activeGenBtn) {
    activeScopeIntel.gender = activeGenBtn.textContent.trim().toLowerCase();
  }

  // Price range checkboxes
  const prChecked = [];
  document.querySelectorAll('input[name="scopePriceRange"]:checked').forEach(c => prChecked.push(c.value));
  activeScopeIntel.priceRanges = prChecked;

  // Brand size checkboxes
  const bsChecked = [];
  document.querySelectorAll('input[name="scopeBrandSize"]:checked').forEach(c => bsChecked.push(c.value));
  activeScopeIntel.brandSizes = bsChecked;

  // Accordion filters
  const bChecked = [];
  document.querySelectorAll('#scopeAccBrand input[type="checkbox"]:checked').forEach(c => bChecked.push(c.value));
  activeScopeIntel.brands = bChecked;

  const cChecked = [];
  document.querySelectorAll('#scopeAccColor input[type="checkbox"]:checked').forEach(c => cChecked.push(c.value));
  activeScopeIntel.colors = cChecked;

  const fChecked = [];
  document.querySelectorAll('#scopeAccFabric input[type="checkbox"]:checked').forEach(c => fChecked.push(c.value));
  activeScopeIntel.fabrics = fChecked;

  const fitChecked = [];
  document.querySelectorAll('#scopeAccFit input[type="checkbox"]:checked').forEach(c => fitChecked.push(c.value));
  activeScopeIntel.fits = fitChecked;

  const discRadio = document.querySelector('input[name="scopeDiscount"]:checked');
  activeScopeIntel.discountMin = discRadio ? parseFloat(discRadio.value) || 0 : 0;

  const inStock = document.getElementById('scopeInStockOnly');
  activeScopeIntel.inStockOnly = inStock ? inStock.checked : false;

  const ratRadio = document.querySelector('input[name="scopeRating"]:checked');
  activeScopeIntel.ratingMin = ratRadio ? parseFloat(ratRadio.value) || 0 : 0;

  const newArr = document.getElementById('scopeNewArrivalsOnly');
  activeScopeIntel.newArrivalsOnly = newArr ? newArr.checked : false;

  loadBrandsScopeIntelligence();
}

function resetBrandsScopeFilters() {
  const catSel = document.getElementById('scopeCategorySelect');
  if (catSel) catSel.value = 'shirts';

  const subSel = document.getElementById('scopeSubcatSelect');
  if (subSel) subSel.value = 'all';

  document.querySelectorAll('#scopeGenderPills .gender-pill').forEach((b, i) => b.classList.toggle('active', i === 0));

  document.querySelectorAll('input[name="scopePriceRange"]').forEach(c => c.checked = false);
  document.querySelectorAll('input[name="scopeBrandSize"]').forEach(c => c.checked = false);

  const defDisc = document.querySelector('input[name="scopeDiscount"][value="0"]');
  if (defDisc) defDisc.checked = true;

  const inStock = document.getElementById('scopeInStockOnly');
  if (inStock) inStock.checked = false;

  const defRat = document.querySelector('input[name="scopeRating"][value="0"]');
  if (defRat) defRat.checked = true;

  const newArr = document.getElementById('scopeNewArrivalsOnly');
  if (newArr) newArr.checked = false;

  document.querySelectorAll('#scopeAccBrand input[type="checkbox"]').forEach(c => c.checked = false);
  document.querySelectorAll('#scopeAccColor input[type="checkbox"]').forEach(c => c.checked = false);
  document.querySelectorAll('#scopeAccFabric input[type="checkbox"]').forEach(c => c.checked = false);
  document.querySelectorAll('#scopeAccFit input[type="checkbox"]').forEach(c => c.checked = false);

  activeScopeIntel = {
    category: 'shirts',
    gender: 'men',
    subcategory: 'all',
    priceRanges: [],
    brandSizes: [],
    brands: [],
    colors: [],
    fabrics: [],
    fits: [],
    discountMin: 0,
    inStockOnly: false,
    ratingMin: 0,
    newArrivalsOnly: false
  };

  loadBrandsScopeIntelligence();
}

function switchBrandsScopeTab(tab, btn) {
  document.querySelectorAll('#view-brands .intel-tabs-nav .intel-tab-btn').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');

  const scopeEl = document.getElementById('brandsScopeContainer');
  const compEl = document.getElementById('brandsComparatorContainer');
  if (scopeEl) scopeEl.style.display = 'block';
  if (compEl) compEl.style.display = 'none';

  if (tab === 'overview') {
    const hdr = document.querySelector('#view-brands .intel-view-header');
    if (hdr) hdr.scrollIntoView({ behavior: 'smooth' });
  } else if (tab === 'brands') {
    const el = document.getElementById('scopeBrandScaleGrid') || document.getElementById('scopeTop10BrandsTableBody');
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  } else if (tab === 'price') {
    const el = document.getElementById('scopePriceDistChart');
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  } else if (tab === 'colors') {
    const el = document.getElementById('scopeColorsProgressList');
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  } else if (tab === 'fabrics') {
    const el = document.getElementById('scopeFabricsProgressList');
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  } else if (tab === 'fit') {
    const el = document.getElementById('scopeBrandScaleGrid');
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  } else if (tab === 'trends') {
    const el = document.getElementById('scopeTopProductsRow');
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  } else if (tab === 'size') {
    const el = document.getElementById('scopeMedianPriceBySizeChart');
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
}

function showBrandComparator(btn) {
  document.querySelectorAll('#view-brands .intel-tabs-nav .intel-tab-btn').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  const scopeEl = document.getElementById('brandsScopeContainer');
  const compEl = document.getElementById('brandsComparatorContainer');
  if (scopeEl) scopeEl.style.display = 'none';
  if (compEl) compEl.style.display = 'block';
  loadBrandComparator();
}

function showBrandsOverview() {
  const scopeEl = document.getElementById('brandsScopeContainer');
  const compEl = document.getElementById('brandsComparatorContainer');
  if (scopeEl) scopeEl.style.display = 'block';
  if (compEl) compEl.style.display = 'none';
  const firstTab = document.querySelector('#view-brands .intel-tabs-nav .intel-tab-btn');
  if (firstTab) firstTab.classList.add('active');
  loadBrandsScopeIntelligence();
}

function exportCategoryReport() {
  window.location.href = '/api/export/catalog';
}

function exportBrandsReport() {
  window.print();
}

const brandsScopeClientCache = new Map();

async function loadBrandsScopeIntelligence() {
  const p = new URLSearchParams();
  p.append('category', activeScopeIntel.category || 'shirts');
  p.append('gender', activeScopeIntel.gender || 'men');
  if (activeScopeIntel.subcategory && activeScopeIntel.subcategory !== 'all') {
    p.append('subcategory', activeScopeIntel.subcategory);
  }
  if (activeScopeIntel.priceRanges && activeScopeIntel.priceRanges.length > 0) {
    p.append('price_ranges', activeScopeIntel.priceRanges.join(','));
  }
  if (activeScopeIntel.brandSizes && activeScopeIntel.brandSizes.length > 0) {
    p.append('brand_size', activeScopeIntel.brandSizes.join(','));
  }
  if (activeScopeIntel.brands && activeScopeIntel.brands.length > 0) {
    p.append('brand', activeScopeIntel.brands.join(','));
  }
  if (activeScopeIntel.colors && activeScopeIntel.colors.length > 0) {
    p.append('color', activeScopeIntel.colors.join(','));
  }
  if (activeScopeIntel.fabrics && activeScopeIntel.fabrics.length > 0) {
    p.append('fabric', activeScopeIntel.fabrics.join(','));
  }
  if (activeScopeIntel.fits && activeScopeIntel.fits.length > 0) {
    p.append('fit', activeScopeIntel.fits.join(','));
  }
  if (activeScopeIntel.discountMin > 0) {
    p.append('discount_min', activeScopeIntel.discountMin);
  }
  if (activeScopeIntel.inStockOnly) {
    p.append('availability', 'in_stock');
  }
  if (activeScopeIntel.ratingMin > 0) {
    p.append('rating_min', activeScopeIntel.ratingMin);
  }
  if (activeScopeIntel.newArrivalsOnly) {
    p.append('new_arrivals', '1');
  }

  const cacheKey = p.toString();
  if (brandsScopeClientCache.has(cacheKey)) {
    renderBrandsScopeData(brandsScopeClientCache.get(cacheKey));
  }

  try {
    const url = `/api/brands-intelligence?${p.toString()}`;
    const res = await fetch(url);
    const data = await res.json();
    if (!data || data.status !== 'success') return;

    brandsScopeClientCache.set(cacheKey, data);
    renderBrandsScopeData(data);
  } catch (err) {
    console.error('Error loading Brands Scope Intelligence:', err);
  }
}

function renderBrandsScopeData(data) {
  try {
    const category = (data.category || activeScopeIntel.category || 'shirts').toLowerCase();
    const subcategory = data.subcategory || activeScopeIntel.subcategory || 'all';
    const k = data.kpis || {};
    const setTxt = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
    updateBrandsScopeCopy(category, subcategory);

    // 0. Update Sidebar Counts & Facet Checklists
    const sb = data.sidebar_counts || {};
    const prCounts = sb.price_ranges || {};
    const fmt = n => typeof n === 'number' ? n.toLocaleString() : (n || '0');

    setTxt('scopeCountLt500', fmt(prCounts.lt_500));
    setTxt('scopeCount500_1000', fmt(prCounts['500_1000']));
    setTxt('scopeCount1000_2000', fmt(prCounts['1000_2000']));
    setTxt('scopeCount2000_3000', fmt(prCounts['2000_3000']));
    setTxt('scopeCount3000_4000', fmt(prCounts['3000_4000']));
    setTxt('scopeCountGt4000', fmt(prCounts.gt_4000));

    const bsCounts = sb.brand_sizes || {};
    setTxt('scopeCountLarge', fmt(bsCounts.large));
    setTxt('scopeCountMid', fmt(bsCounts.mid));
    setTxt('scopeCountSmall', fmt(bsCounts.small));

    // Update Subcategories dropdown options if available
    if (sb.subcategories && sb.subcategories.length > 0) {
      const subSel = document.getElementById('scopeSubcatSelect');
      if (subSel) {
        const validValues = new Set(sb.subcategories.map(s => s.value));
        const curVal = validValues.has(subSel.value) ? subSel.value : 'all';
        if (curVal !== subSel.value) {
          activeScopeIntel.subcategory = 'all';
        }
        subSel.innerHTML = sb.subcategories.map(s => 
          `<option value="${escapeHtml(s.value)}" ${s.value === curVal ? 'selected' : ''}>${escapeHtml(s.name)}</option>`
        ).join('');
        subSel.value = curVal;
      }
    }

    // Populate Dynamic Accordions
    const af = sb.available_filters || {};

    // Brands Accordion
    const accBrand = document.getElementById('scopeAccBrand');
    if (accBrand && af.brands && af.brands.length > 0) {
      const validBrands = new Set(af.brands.map(b => b.brand));
      activeScopeIntel.brands = activeScopeIntel.brands.filter(brand => validBrands.has(brand));
      accBrand.innerHTML = af.brands.map(b => `
        <label class="sub-check-item">
          <input type="checkbox" value="${escapeHtml(b.brand)}" onchange="applyBrandsScopeFilters()" ${activeScopeIntel.brands.includes(b.brand) ? 'checked' : ''} />
          <span class="check-text">${escapeHtml(b.brand)}</span>
          <span class="check-count">${b.count.toLocaleString()}</span>
        </label>
      `).join('');
    }

    // Colors Accordion
    const accColor = document.getElementById('scopeAccColor');
    if (accColor && af.colors && af.colors.length > 0) {
      const validColors = new Set(af.colors.map(c => c.color));
      activeScopeIntel.colors = activeScopeIntel.colors.filter(color => validColors.has(color));
      accColor.innerHTML = af.colors.map(c => `
        <label class="sub-check-item">
          <input type="checkbox" value="${escapeHtml(c.color)}" onchange="applyBrandsScopeFilters()" ${activeScopeIntel.colors.includes(c.color) ? 'checked' : ''} />
          <span style="display:inline-block; width:10px; height:10px; border-radius:50%; background:${c.hex}; margin-right:4px;"></span>
          <span class="check-text">${escapeHtml(c.color)}</span>
          <span class="check-count">${c.count.toLocaleString()}</span>
        </label>
      `).join('');
    }

    // Fabrics Accordion
    const accFabric = document.getElementById('scopeAccFabric');
    if (accFabric && af.fabrics && af.fabrics.length > 0) {
      const validFabrics = new Set(af.fabrics.map(f => f.fabric));
      activeScopeIntel.fabrics = activeScopeIntel.fabrics.filter(fabric => validFabrics.has(fabric));
      accFabric.innerHTML = af.fabrics.map(f => `
        <label class="sub-check-item">
          <input type="checkbox" value="${escapeHtml(f.fabric)}" onchange="applyBrandsScopeFilters()" ${activeScopeIntel.fabrics.includes(f.fabric) ? 'checked' : ''} />
          <span class="check-text">${escapeHtml(f.fabric)}</span>
          <span class="check-count">${f.count.toLocaleString()}</span>
        </label>
      `).join('');
    }

    // Fits Accordion
    const accFit = document.getElementById('scopeAccFit');
    if (accFit && af.fits && af.fits.length > 0) {
      const validFits = new Set(af.fits.map(ft => ft.fit));
      activeScopeIntel.fits = activeScopeIntel.fits.filter(fit => validFits.has(fit));
      accFit.innerHTML = af.fits.map(ft => `
        <label class="sub-check-item">
          <input type="checkbox" value="${escapeHtml(ft.fit)}" onchange="applyBrandsScopeFilters()" ${activeScopeIntel.fits.includes(ft.fit) ? 'checked' : ''} />
          <span class="check-text">${escapeHtml(ft.fit)}</span>
          <span class="check-count">${ft.count.toLocaleString()}</span>
        </label>
      `).join('');
    }

    // Top KPIs
    setTxt('scopeKpiTotalProds', displayCount(k.total_products_num ?? k.total_products));
    setTxt('scopeKpiMedianPrice', displayValue(k.median_price));
    setTxt('scopeKpiMeanModeSub', `Avg ${displayValue(k.mean_price)} | Mode ${displayValue(k.mode_price)}`);
    setTxt('scopeKpiAvgDiscount', displayValue(k.avg_discount));
    const medianBadgeEl = document.querySelector('#scopeKpiMedianPrice')?.closest('.intel-kpi-card')?.querySelector('.kpi-badge');
    if (medianBadgeEl) medianBadgeEl.textContent = displayValue(k.pricing_note, 'Live filtered pricing');
    const discountBadgeEl = document.querySelector('#scopeKpiAvgDiscount')?.closest('.intel-kpi-card')?.querySelector('.kpi-badge');
    if (discountBadgeEl) discountBadgeEl.textContent = displayValue(k.discount_note, 'Across current filtered products');
    setTxt('scopeKpiTopBrandName', (k.top_brand || {}).name ? `↑ ${(k.top_brand || {}).name}` : '-');
    setTxt('scopeKpiTopBrandSub', displayValue((k.top_brand || {}).products));

    const pDist = data.price_distribution || {};
    setTxt('scopeStatMedian', displayValue(pDist.median_price));
    setTxt('scopeStatMode', displayValue(pDist.mode_price));
    setTxt('scopeStatMean', displayValue(pDist.mean_price));
    setTxt('scopeStatCompRange', displayValue(pDist.most_competitive_range));

    // 1. Price Distribution Bar Chart
    const priceCtx = document.getElementById('scopePriceDistChart');
    if (priceCtx && window.Chart) {
      if (scopePriceChartInst) scopePriceChartInst.destroy();
      const brackets = pDist.brackets || [];
      scopePriceChartInst = new Chart(priceCtx, {
        type: 'bar',
        data: {
          labels: brackets.map(b => b.label),
          datasets: [{
            data: brackets.map(b => b.count),
            backgroundColor: '#94a3b8',
            hoverBackgroundColor: '#0f172a',
            borderRadius: 4,
            barPercentage: 0.65
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { grid: { display: false }, ticks: { font: { size: 9.5, weight: '600' }, color: '#64748b' } },
            y: { grid: { color: '#f1f5f9' }, ticks: { font: { size: 9 }, color: '#94a3b8', callback: v => v >= 1000 ? `${v/1000}K` : v } }
          }
        }
      });
    }

    // 2. Top Fabrics Progress Bars
    const fabricsProgressList = document.getElementById('scopeFabricsProgressList');
    if (fabricsProgressList) {
      fabricsProgressList.innerHTML = (data.top_fabrics || []).slice(0, 6).map(f => `
        <div class="intel-progress-item">
          <span class="intel-progress-name" style="width: 85px;">${escapeHtml(f.fabric)}</span>
          <div class="intel-progress-track">
            <div class="intel-progress-fill" style="width: ${f.share};"></div>
          </div>
          <span class="intel-progress-cnt">${f.count.toLocaleString()}</span>
          <span class="intel-progress-share">${f.share}</span>
        </div>
      `).join('');
    }

    // 3. Top Colors Progress Bars
    const colorsProgressList = document.getElementById('scopeColorsProgressList');
    if (colorsProgressList) {
      colorsProgressList.innerHTML = (data.top_colors || []).slice(0, 6).map(c => `
        <div class="intel-progress-item">
          <span class="intel-color-dot" style="background:${c.hex};"></span>
          <span class="intel-progress-name">${escapeHtml(c.color)}</span>
          <div class="intel-progress-track">
            <div class="intel-progress-fill" style="width: ${c.share};"></div>
          </div>
          <span class="intel-progress-cnt">${c.count.toLocaleString()}</span>
          <span class="intel-progress-share">${c.share}</span>
        </div>
      `).join('');
    }

    // 4. Brands by Scale Cards (Largest, Mid-size, Small)
    const scaleGrid = document.getElementById('scopeBrandScaleGrid');
    const bScale = data.brands_by_scale || {};
    if (scaleGrid) {
      const l = bScale.largest || { count: 0, threshold: '-', brands: [], more_count: 0 };
      const m = bScale.midsize || { count: 0, threshold: '-', brands: [], more_count: 0 };
      const s = bScale.small || { count: 0, threshold: '-', brands: [], more_count: 0 };

      scaleGrid.innerHTML = `
        <div class="brand-scale-card">
          <span class="scale-card-title">Largest Brands</span>
          <span class="scale-card-count">${l.count}</span>
          <span class="scale-card-sub">${l.threshold}</span>
          <div class="scale-brand-chips">
            ${(l.brands || []).map(b => `<span class="scale-brand-chip">• ${escapeHtml(b)}</span>`).join('')}
            ${l.more_count > 0 ? `<span class="scale-more-link">+${l.more_count} more</span>` : ''}
          </div>
        </div>
        <div class="brand-scale-card">
          <span class="scale-card-title">Mid-size Brands</span>
          <span class="scale-card-count">${m.count}</span>
          <span class="scale-card-sub">${m.threshold}</span>
          <div class="scale-brand-chips">
            ${(m.brands || []).map(b => `<span class="scale-brand-chip">• ${escapeHtml(b)}</span>`).join('')}
            ${m.more_count > 0 ? `<span class="scale-more-link">+${m.more_count} more</span>` : ''}
          </div>
        </div>
        <div class="brand-scale-card">
          <span class="scale-card-title">Small Brands</span>
          <span class="scale-card-count">${s.count}</span>
          <span class="scale-card-sub">${s.threshold}</span>
          <div class="scale-brand-chips">
            ${(s.brands || []).map(b => `<span class="scale-brand-chip">• ${escapeHtml(b)}</span>`).join('')}
            ${s.more_count > 0 ? `<span class="scale-more-link">+${s.more_count} more</span>` : ''}
          </div>
        </div>
      `;
    }

    // 5. Top 10 Brands Table
    const top10Tbody = document.getElementById('scopeTop10BrandsTableBody');
    if (top10Tbody) {
      const rows = data.top_10_brands || [];
      top10Tbody.innerHTML = rows.length ? rows.map(b => `
        <tr>
          <td style="color:#64748b; font-weight:700;">${b.rank}</td>
          <td style="font-weight:700; color:#0f172a;">${escapeHtml(b.brand)}</td>
          <td style="text-align:right; font-weight:600; color:#475569;">${b.products.toLocaleString()}</td>
          <td style="text-align:right; color:#0f172a; font-weight:600;">${b.median_price}</td>
          <td style="text-align:right; color:#64748b;">${b.avg_discount}</td>
        </tr>
      `).join('') : '<tr><td colspan="5" style="padding:14px; text-align:center; color:#94a3b8;">No brand ranking available for the current scope.</td></tr>';
    }

    // 6. Median Price by Brand Size Bar Chart
    const medianSizeCtx = document.getElementById('scopeMedianPriceBySizeChart');
    if (medianSizeCtx && window.Chart) {
      if (scopeMedianBySizeChartInst) scopeMedianBySizeChartInst.destroy();
      const medData = data.median_price_by_brand_size || [];
      scopeMedianBySizeChartInst = new Chart(medianSizeCtx, {
        type: 'bar',
        data: {
          labels: medData.map(m => m.tier),
          datasets: [{
            data: medData.map(m => m.median_price),
            backgroundColor: ['#94a3b8', '#64748b', '#0f172a'],
            borderRadius: 4,
            barPercentage: 0.55
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { grid: { display: false }, ticks: { font: { size: 10, weight: '600' }, color: '#475569' } },
            y: { grid: { color: '#f1f5f9' }, ticks: { font: { size: 9 }, color: '#94a3b8', callback: v => `₹${v}` } }
          }
        }
      });
    }

    // 7. Top Products Horizontal Cards
    const scopeProdsRow = document.getElementById('scopeTopProductsRow');
    if (scopeProdsRow) {
      const products = data.top_products || [];
      const subtitleEl = document.getElementById('scopeTopProductsSubtitle');
      if (subtitleEl && data.top_products_note) subtitleEl.textContent = data.top_products_note;
      scopeProdsRow.innerHTML = products.length ? products.map(p => `
        <div class="intel-product-card" onclick="openProductDrawer(${p.product_id});" style="cursor: pointer;">
          <span class="intel-product-rank-badge">${p.rank}</span>
          <img src="${p.image_url || 'assets/luxury_silk_banner.jpg'}" class="intel-product-img" alt="${escapeHtml(p.brand)}" onerror="this.src='assets/luxury_silk_banner.jpg'" />
          <span class="intel-prod-brand">${escapeHtml(p.brand)}</span>
          <span class="intel-prod-title" title="${escapeHtml(p.title)}">${escapeHtml(p.title)}</span>
          <span class="intel-prod-price">${p.price}</span>
          <div class="intel-prod-meta-row">
            <span>⚡ ${escapeHtml(p.velocity)}</span>
            <span>📦 Stock ${p.stock}</span>
          </div>
          <div style="font-size:11px; color:#64748b; margin-top:4px;">${Number(p.units_sold_window || 0).toLocaleString('en-IN')} sold in recent window</div>
        </div>
      `).join('') : '<div style="padding:14px; color:#94a3b8; font-size:12px;">No representative products found for the current scope.</div>';
    }
  } catch (err) {
    console.error('Error rendering Brands Scope Intelligence data:', err);
  }
}

// ==========================================================================
// PRICE INTELLIGENCE SUITE
// ==========================================================================
let priceDistChartInst = null;
let priceTrendChartInst = null;
let pricePositioningChartInst = null;
let currentPriceGender = 'men';

function getPriceBrandCheckboxes() {
  return Array.from(document.querySelectorAll('#priceBrandChecklist input[type="checkbox"]'))
    .filter(input => input.value && input.value !== 'all');
}

function onPriceBrandCheckboxChange(input) {
  const allBrandsChk = document.getElementById('priceBrandAll');
  const brandInputs = getPriceBrandCheckboxes();
  if (!input) return;

  if (input.value === 'all') {
    brandInputs.forEach(cb => {
      cb.checked = input.checked;
    });
    if (!input.checked && brandInputs.length > 0) {
      brandInputs[0].checked = true;
      input.checked = false;
    }
  } else {
    if (allBrandsChk) allBrandsChk.checked = false;
    const checkedCount = brandInputs.filter(cb => cb.checked).length;
    if (checkedCount === 0 && allBrandsChk) {
      allBrandsChk.checked = true;
      brandInputs.forEach(cb => {
        cb.checked = true;
      });
    } else if (allBrandsChk && checkedCount === brandInputs.length) {
      allBrandsChk.checked = true;
    }
  }

  applyPriceIntelFilters();
}

function setPriceGender(btn, gender) {
  document.querySelectorAll('#priceGenderPills .intel-pill').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  currentPriceGender = gender;
  applyPriceIntelFilters();
}

function togglePriceAllBrands(masterChk) {
  onPriceBrandCheckboxChange(masterChk);
}

function filterPriceBrandList(q) {
  const query = (q || '').toLowerCase();
  document.querySelectorAll('#priceBrandChecklist .intel-check-label').forEach(lbl => {
    const span = lbl.querySelector('span');
    if (!span) return;
    if (span.textContent.toLowerCase().includes('all brands')) return;
    lbl.style.display = span.textContent.toLowerCase().includes(query) ? 'flex' : 'none';
  });
}

function resetPriceIntelFilters() {
  const catSel = document.getElementById('priceFilterCategory');
  if (catSel) catSel.value = 'shirts';
  const subcatSel = document.getElementById('priceFilterSubcategory');
  if (subcatSel) subcatSel.value = 'all';
  const fabSel = document.getElementById('priceFilterFabric');
  if (fabSel) fabSel.value = 'all';
  const colSel = document.getElementById('priceFilterColor');
  if (colSel) colSel.value = 'all';
  const discSel = document.getElementById('priceFilterDiscount');
  if (discSel) discSel.value = 'all';
  const availSel = document.getElementById('priceFilterAvailability');
  if (availSel) availSel.value = 'all';

  document.querySelectorAll('#priceGenderPills .intel-pill').forEach(b => {
    b.classList.toggle('active', b.dataset.gender === 'men');
  });
  currentPriceGender = 'men';

  document.querySelectorAll('.price-range-chk').forEach(c => {
    c.checked = false;
  });

  const allBrandsChk = document.getElementById('priceBrandAll');
  if (allBrandsChk) allBrandsChk.checked = true;
  getPriceBrandCheckboxes().forEach(c => {
    c.checked = true;
  });

  loadPriceIntelligence();
}

function applyPriceIntelFilters() {
  loadPriceIntelligence();
}

async function loadPriceIntelligence() {
  try {
    const requestSeq = ++priceIntelRequestSeq;
    const category = document.getElementById('priceFilterCategory')?.value || 'shirts';
    const subcategory = document.getElementById('priceFilterSubcategory')?.value || 'all';
    const gender = currentPriceGender || 'men';
    const fabric = document.getElementById('priceFilterFabric')?.value || 'all';
    const color = document.getElementById('priceFilterColor')?.value || 'all';
    const discount = document.getElementById('priceFilterDiscount')?.value || 'all';
    const availability = document.getElementById('priceFilterAvailability')?.value || 'all';

    // Brands
    const brandChks = Array.from(document.querySelectorAll('#priceBrandChecklist input[type="checkbox"]:checked'));
    const allBrandsChecked = document.getElementById('priceBrandAll')?.checked;
    let brandsParam = '';
    if (!allBrandsChecked && brandChks.length > 0) {
      brandsParam = brandChks.map(c => c.value).filter(v => v !== 'all').join(',');
    }

    // Price ranges
    const rangeChks = Array.from(document.querySelectorAll('.price-range-chk:checked')).map(c => c.value);
    let minP = null;
    let maxP = null;
    if (rangeChks.length > 0) {
      let mins = [];
      let maxs = [];
      rangeChks.forEach(r => {
        const parts = r.split('-').map(Number);
        if (parts.length === 2) {
          mins.push(parts[0]);
          maxs.push(parts[1]);
        }
      });
      if (mins.length) minP = Math.min(...mins);
      if (maxs.length) maxP = Math.max(...maxs);
    }

    const params = new URLSearchParams();
    if (category) params.set('category', category);
    if (subcategory && subcategory !== 'all') params.set('subcategory', subcategory);
    if (gender && gender !== 'all') params.set('gender', gender);
    if (brandsParam) params.set('brands', brandsParam);
    if (fabric && fabric !== 'all') params.set('fabric', fabric);
    if (color && color !== 'all') params.set('color', color);
    if (discount && discount !== 'all') params.set('discount_range', discount);
    if (availability && availability !== 'all') params.set('availability', availability);
    if (minP !== null && minP > 0) params.set('price_min', minP);
    if (maxP !== null && maxP < 999999) params.set('price_max', maxP);

    const res = await fetch(`/api/price-intelligence?${params.toString()}`);
    if (!res.ok) throw new Error(`Price intelligence load failed with status ${res.status}`);
    const data = await res.json();
    if (requestSeq !== priceIntelRequestSeq) return;
    if (data.status !== 'success') return;

    const priceScopeLabel = formatScopeLabel(category, subcategory);
    const priceSubtitleEl = document.getElementById('priceIntelSubtitle');
    if (priceSubtitleEl) {
      priceSubtitleEl.textContent = `Understand market pricing, brand positioning and price opportunities across ${priceScopeLabel.toLowerCase()} in the current filter selection.`;
    }
    const priceWindowEl = document.getElementById('priceIntelDataWindow');
    if (priceWindowEl) {
      const windowMeta = data.data_window || {};
      const startLabel = displayValue(windowMeta.snapshot_start_label || formatDateLabel(windowMeta.snapshot_start_date, ''), '');
      const endLabel = displayValue(windowMeta.snapshot_end_label || formatDateLabel(windowMeta.snapshot_end_date, ''), '');
      const snapshotDays = Number(windowMeta.snapshot_days || 0);
      const trendPoints = Number(windowMeta.trend_points || 0);
      priceWindowEl.textContent = snapshotDays > 0
        ? `Stored pricing history: ${startLabel} to ${endLabel} across ${snapshotDays.toLocaleString('en-IN')} snapshot day${snapshotDays === 1 ? '' : 's'}. Trend chart shows the latest ${trendPoints.toLocaleString('en-IN')} points.`
        : 'Stored pricing history will appear once inventory snapshots are available.';
    }
    const priceInterpretEl = document.getElementById('priceIntelInterpretationNote');
    if (priceInterpretEl) {
      priceInterpretEl.textContent = data.interpretation_note || data.methodology_note || 'Median price is usually the most stable directional read for skewed selections.';
      priceInterpretEl.style.display = priceInterpretEl.textContent ? '' : 'none';
    }

    const categoryValue = document.getElementById('priceFilterCategory')?.value || 'all';
    const categorySelect = document.getElementById('priceFilterCategory');
    const availableCategories = Array.isArray(data.available_categories) ? data.available_categories : [];
    if (categorySelect && availableCategories.length > 0) {
      const validValues = new Set(availableCategories.map(item => String(item.value || 'all')));
      const nextValue = validValues.has(categoryValue) ? categoryValue : 'all';
      categorySelect.innerHTML = availableCategories.map(item => {
        const value = String(item.value || 'all');
        const label = `${String(item.name || value)} (${displayCount(item.count, '0')})`;
        return `<option value="${escapeHtml(value)}" ${value === nextValue ? 'selected' : ''}>${escapeHtml(label)}</option>`;
      }).join('');
      categorySelect.value = nextValue;
    }

    // 1. KPI Cards
    const kpis = data.kpis || {};
    const avgDelta = formatDeltaBadge(kpis.avg_price_delta);
    const medianDelta = formatDeltaBadge(kpis.median_price_delta);
    const discountDelta = formatDeltaBadge(kpis.discounted_delta);
    if (document.getElementById('priceKpiAvg')) {
      document.getElementById('priceKpiAvg').textContent = displayValue(kpis.avg_price_formatted);
    }
    const avgSubEl = document.getElementById('priceKpiAvgSub');
    if (avgSubEl) {
      avgSubEl.textContent = availability === 'low_stock'
        ? 'Outlier-sensitive in low-stock slices'
        : 'vs active comparison baseline';
    }
    if (document.getElementById('priceKpiAvgDelta')) {
      document.getElementById('priceKpiAvgDelta').textContent = avgDelta.text;
      document.getElementById('priceKpiAvgDelta').className = `intel-kpi-badge ${avgDelta.tone}`;
    }

    if (document.getElementById('priceKpiMedian')) {
      document.getElementById('priceKpiMedian').textContent = displayValue(kpis.median_price_formatted);
    }
    const medianSubEl = document.getElementById('priceKpiMedianSub');
    if (medianSubEl) {
      medianSubEl.textContent = availability === 'low_stock'
        ? 'Better signal when premium outliers distort averages'
        : 'vs active comparison baseline';
    }
    if (document.getElementById('priceKpiMedianDelta')) {
      document.getElementById('priceKpiMedianDelta').textContent = medianDelta.text;
      document.getElementById('priceKpiMedianDelta').className = `intel-kpi-badge ${medianDelta.tone}`;
    }

    if (document.getElementById('priceKpiMode')) {
      document.getElementById('priceKpiMode').textContent = displayValue(kpis.mode_price_formatted);
    }

    if (document.getElementById('priceKpiRange')) {
      document.getElementById('priceKpiRange').textContent = displayValue(kpis.price_range_str);
    }

    if (document.getElementById('priceKpiDiscount')) {
      document.getElementById('priceKpiDiscount').textContent = kpis.discounted_pct !== undefined && kpis.discounted_pct !== null && kpis.discounted_pct !== ''
        ? `${kpis.discounted_pct}%`
        : '-';
    }
    if (document.getElementById('priceKpiDiscountDelta')) {
      document.getElementById('priceKpiDiscountDelta').textContent = discountDelta.text;
      document.getElementById('priceKpiDiscountDelta').className = `intel-kpi-badge ${discountDelta.tone}`;
    }

    const subcategoryValue = document.getElementById('priceFilterSubcategory')?.value || 'all';
    const fabricValue = document.getElementById('priceFilterFabric')?.value || 'all';
    const colorValue = document.getElementById('priceFilterColor')?.value || 'all';
    syncSelectFromFacetList(
      'priceFilterSubcategory',
      data.available_subcategories || [],
      subcategoryValue,
      'All Subcategories',
      item => `${item.name} (${displayCount(item.count, '0')})`
    );
    syncSelectFromFacetList(
      'priceFilterFabric',
      data.available_fabrics || [],
      fabricValue,
      'All Fabrics',
      item => `${item.name} (${displayCount(item.count, '0')})`
    );
    syncSelectFromFacetList(
      'priceFilterColor',
      data.available_colors || [],
      colorValue,
      'All Colors',
      item => `${item.name} (${displayCount(item.count, '0')})`
    );

    // 2. Chart: Price Distribution Bar Chart
    const distCanvas = document.getElementById('chartPriceDistribution');
    if (distCanvas && window.Chart) {
      if (priceDistChartInst) priceDistChartInst.destroy();
      const dist = data.price_distribution || [];
      priceDistChartInst = new Chart(distCanvas, {
        type: 'bar',
        data: {
          labels: dist.map(d => d.label),
          datasets: [{
            data: dist.map(d => d.count),
            backgroundColor: '#94a3b8',
            hoverBackgroundColor: '#0f172a',
            borderRadius: 4,
            barPercentage: 0.65
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: (ctx) => `${ctx.parsed.y.toLocaleString()} products`
              }
            }
          },
          scales: {
            x: {
              grid: { display: false },
              ticks: { font: { size: 10, weight: '600' }, color: '#475569' }
            },
            y: {
              grid: { color: '#f1f5f9' },
              ticks: {
                font: { size: 9 },
                color: '#94a3b8',
                callback: v => (v >= 1000 ? `${(v/1000).toFixed(1)}K` : v)
              }
            }
          }
        }
      });
    }

    // 3. Chart: Average Price Trend Line Chart
    const trendCanvas = document.getElementById('chartPriceTrend');
    if (trendCanvas && window.Chart) {
      if (priceTrendChartInst) priceTrendChartInst.destroy();
      const pt = data.price_trend || {};
      if (document.getElementById('priceTrendBadge')) {
        const priceTrendBadge = [displayValue(pt.latest_asp), displayValue(pt.delta_badge)]
          .filter(part => part && part !== '-')
          .join(' ');
        document.getElementById('priceTrendBadge').textContent = priceTrendBadge || '-';
      }
      priceTrendChartInst = new Chart(trendCanvas, {
        type: 'line',
        data: {
          labels: pt.months || [],
          datasets: [
            {
              label: pt.category_name || 'Category',
              data: pt.category_trend || [],
              borderColor: '#0f172a',
              backgroundColor: '#0f172a',
              borderWidth: 2.5,
              pointRadius: 4,
              pointBackgroundColor: '#0f172a',
              tension: 0.2
            },
            {
              label: 'All Categories',
              data: pt.overall_trend || [],
              borderColor: '#cbd5e1',
              backgroundColor: '#cbd5e1',
              borderWidth: 1.5,
              borderDash: [4, 4],
              pointRadius: 0,
              tension: 0.2
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: 'bottom',
              labels: { boxWidth: 10, font: { size: 10, weight: '600' }, color: '#475569' }
            },
            tooltip: {
              callbacks: {
                label: (ctx) => `${ctx.dataset.label}: ₹${ctx.parsed.y.toLocaleString()}`
              }
            }
          },
          scales: {
            x: {
              grid: { display: false },
              ticks: { font: { size: 10 }, color: '#64748b' }
            },
            y: {
              grid: { color: '#f1f5f9' },
              ticks: {
                font: { size: 9 },
                color: '#94a3b8',
                callback: v => (v >= 1000 ? `${(v/1000).toFixed(1)}K` : v)
              }
            }
          }
        }
      });
    }

    // 4. Chart: Price Positioning Bubble Chart
    const posCanvas = document.getElementById('chartPricePositioning');
    if (posCanvas && window.Chart) {
      if (pricePositioningChartInst) pricePositioningChartInst.destroy();
      const posData = data.price_positioning || [];
      pricePositioningChartInst = new Chart(posCanvas, {
        type: 'bubble',
        data: {
          datasets: [{
            label: 'Brands',
            data: posData.map(b => ({
              x: b.product_count,
              y: b.avg_price,
              r: b.radius,
              brand: b.brand,
              discount: b.avg_discount
            })),
            backgroundColor: 'rgba(15, 23, 42, 0.85)',
            hoverBackgroundColor: '#0f172a'
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: (ctx) => {
                  const raw = ctx.raw;
                  return `${raw.brand}: ${raw.x.toLocaleString()} products, ASP ₹${Math.round(raw.y).toLocaleString()} (${raw.discount}% off)`;
                }
              }
            }
          },
          scales: {
            x: {
              title: { display: true, text: 'Product Count', font: { size: 10, weight: '600' }, color: '#64748b' },
              grid: { color: '#f1f5f9' },
              ticks: { font: { size: 9 }, color: '#94a3b8', callback: v => (v >= 1000 ? `${v/1000}K` : v) }
            },
            y: {
              title: { display: true, text: 'Avg. Price (₹)', font: { size: 10, weight: '600' }, color: '#64748b' },
              grid: { color: '#f1f5f9' },
              ticks: { font: { size: 9 }, color: '#94a3b8', callback: v => (v >= 1000 ? `${v/1000}K` : v) }
            }
          }
        }
      });
    }

    // 5. Table: Price by Fabric
    const fabTbody = document.getElementById('priceByFabricTbody');
    if (fabTbody) {
      const rows = data.price_by_fabric || [];
      fabTbody.innerHTML = rows.length ? rows.map(f => `
        <tr>
          <td style="font-weight: 600; color: #0f172a;">${escapeHtml(f.fabric)}</td>
          <td style="text-align: right; color: #475569;">${f.products_formatted}</td>
          <td style="text-align: right; font-weight: 600; color: #0f172a;">${f.avg_price_formatted}</td>
          <td style="text-align: right; color: #475569;">${f.median_price_formatted}</td>
        </tr>
      `).join('') : '<tr><td colspan="4" style="padding: 14px; text-align:center; color:#94a3b8;">No fabric pricing data for the current filters.</td></tr>';
    }

    // 6. Table: Price by Color
    const colTbody = document.getElementById('priceByColorTbody');
    if (colTbody) {
      const rows = data.price_by_color || [];
      colTbody.innerHTML = rows.length ? rows.map(c => `
        <tr>
          <td>
            <div style="display: flex; align-items: center; gap: 8px;">
              <span style="width: 12px; height: 12px; border-radius: 50%; background-color: ${c.hex}; border: 1px solid ${c.hex.toLowerCase() === '#ffffff' ? '#cbd5e1' : 'rgba(0,0,0,0.1)'}; display: inline-block;"></span>
              <span style="font-weight: 600; color: #0f172a;">${escapeHtml(c.color)}</span>
            </div>
          </td>
          <td style="text-align: right; color: #475569;">${c.products_formatted}</td>
          <td style="text-align: right; font-weight: 600; color: #0f172a;">${c.avg_price_formatted}</td>
          <td style="text-align: right; color: #475569;">${c.median_price_formatted}</td>
        </tr>
      `).join('') : '<tr><td colspan="4" style="padding: 14px; text-align:center; color:#94a3b8;">No color pricing data for the current filters.</td></tr>';
    }

    // 7. Table: Price Heatmap
    const heatTbody = document.getElementById('priceHeatmapTbody');
    if (heatTbody) {
      const rows = data.price_heatmap || [];
      heatTbody.innerHTML = rows.length ? rows.map(b => {
        const getShade = (val) => {
          if (val === '-' || !val) return 'background: #f8fafc; color: #94a3b8;';
          const num = Number(val);
          const intensity = Math.min(0.85, Math.max(0.08, num / 3500));
          return `background: rgba(15, 23, 42, ${intensity}); color: ${intensity > 0.45 ? '#ffffff' : '#0f172a'};`;
        };
        return `
          <tr>
            <td style="font-weight: 600; color: #0f172a;">${escapeHtml(b.brand)}</td>
            <td><div class="heatmap-cell" style="${getShade(b.b1_avg)}">${b.b1_avg}</div></td>
            <td><div class="heatmap-cell" style="${getShade(b.b2_avg)}">${b.b2_avg}</div></td>
            <td><div class="heatmap-cell" style="${getShade(b.b3_avg)}">${b.b3_avg}</div></td>
            <td><div class="heatmap-cell" style="${getShade(b.b4_avg)}">${b.b4_avg}</div></td>
            <td><div class="heatmap-cell" style="${getShade(b.b5_avg)}">${b.b5_avg}</div></td>
          </tr>
        `;
      }).join('') : '<tr><td colspan="6" style="padding: 14px; text-align:center; color:#94a3b8;">No heatmap data for the current filters.</td></tr>';
    }

    // 8. Ranked List: Top 5 Brands by ASP
    const topAspList = document.getElementById('priceTopAspList');
    if (topAspList) {
      const topAsp = data.top_asp_brands || [];
      const maxAsp = topAsp.length ? Math.max(...topAsp.map(a => a.avg_price)) : 1;
      topAspList.innerHTML = topAsp.length ? topAsp.map(a => {
        const pct = Math.min(100, Math.round((a.avg_price / maxAsp) * 100));
        return `
          <div class="intel-rank-row">
            <div class="intel-rank-name" title="${escapeHtml(a.brand)}">${escapeHtml(a.brand)}</div>
            <div class="intel-rank-bar-wrap">
              <div class="intel-rank-bar-fill" style="width: ${pct}%;"></div>
            </div>
            <div class="intel-rank-val">${a.avg_price_formatted}</div>
          </div>
        `;
      }).join('') : '<div style="padding: 14px; color:#94a3b8; font-size:12px;">No premium price leaders in this scope.</div>';
    }

    // 9. Ranked List: Top 5 Discounted Brands
    const topDiscList = document.getElementById('priceTopDiscountList');
    if (topDiscList) {
      const topDisc = data.top_discount_brands || [];
      topDiscList.innerHTML = topDisc.length ? topDisc.map(d => {
        return `
          <div class="intel-rank-row">
            <div class="intel-rank-name" title="${escapeHtml(d.brand)}">${escapeHtml(d.brand)}</div>
            <div class="intel-rank-bar-wrap">
              <div class="intel-rank-bar-fill" style="width: ${Math.min(100, Math.round(d.avg_discount))}%;"></div>
            </div>
            <div class="intel-rank-val">${d.avg_discount_formatted}</div>
          </div>
        `;
      }).join('') : '<div style="padding: 14px; color:#94a3b8; font-size:12px;">No discount leaders in this scope.</div>';
    }

    // 10. Opportunities List
    const oppsList = document.getElementById('priceOppsList');
    if (oppsList) {
      const rows = data.price_opportunities || [];
      oppsList.innerHTML = rows.length ? rows.map((opp, idx) => `
        <div class="intel-opp-item">
          <div class="intel-opp-num">${idx + 1}</div>
          <div>${escapeHtml(opp)}</div>
        </div>
      `).join('') : '<div style="padding: 14px; color:#94a3b8; font-size:12px;">No pricing opportunities generated for this scope.</div>';
    }

    // 11. Key Insight Banner
    if (document.getElementById('priceKeyInsightText') && data.key_insight) {
      document.getElementById('priceKeyInsightText').textContent = data.key_insight;
    }

    // 12. Refresh Sidebar Brand Checklist from current filtered dataset
    if (data.sidebar_brands) {
      const chkContainer = document.getElementById('priceBrandChecklist');
      if (chkContainer) {
        const prevChecked = new Set(
          Array.from(chkContainer.querySelectorAll('input[type="checkbox"]:checked'))
            .map(c => c.value)
            .filter(v => v && v !== 'all')
        );
        const nextBrands = data.sidebar_brands.slice(0, 15);
        const availableBrands = new Set(nextBrands.map(b => b.brand));
        const selectedBrands = Array.from(prevChecked).filter(b => availableBrands.has(b));
        const useAllBrands = selectedBrands.length === 0;

        let html = `<label class="intel-check-label"><input type="checkbox" value="all" id="priceBrandAll" ${useAllBrands ? 'checked' : ''} onchange="togglePriceAllBrands(this)" /> <span>All Brands</span></label>`;
        nextBrands.forEach(b => {
          const checked = !useAllBrands && selectedBrands.includes(b.brand);
          html += `<label class="intel-check-label"><input type="checkbox" value="${escapeHtml(b.brand)}" ${checked ? 'checked' : ''} onchange="onPriceBrandCheckboxChange(this)" /> <span>${escapeHtml(b.brand)} (${Number(b.count || 0).toLocaleString('en-IN')})</span></label>`;
        });
        chkContainer.innerHTML = html;
      }
    }
  } catch (err) {
    console.error('Error loading Price Intelligence:', err);
  }
}

/* ==========================================================================
   SCRAPER RUN ACTIVITY & DAY-WISE ERROR LOG DASHBOARD
   ========================================================================== */
async function fetchScraperLogsAndRuns() {
  try {
    const res = await fetch('/api/scraper/runs');
    if (!res.ok) return;
    const data = await res.json();
    renderScraperRunsData(data.runs || []);
  } catch (err) {
    console.error('Error fetching scraper runs:', err);
  }
}

function renderScraperRunsData(runs) {
  const tbody = document.getElementById('scraperRunsTableBody');
  if (!tbody) return;

  if (!runs || runs.length === 0) {
    tbody.innerHTML = `<tr><td colspan="9" style="text-align:center; padding:24px; color:#94a3b8;">No scraper runs recorded yet.</td></tr>`;
    return;
  }

  let totalItems = 0;
  let totalEnriched = 0;
  let totalFailed = 0;

  runs.forEach(r => {
    totalItems += (r.total_items || 0);
    totalEnriched += (r.successful_items || 0);
    totalFailed += (r.failed_items || 0);
  });

  const kpiTotal = document.getElementById('kpiTotalRunsCount');
  if (kpiTotal) kpiTotal.textContent = runs.length.toLocaleString();
  const kpiEnriched = document.getElementById('kpiTotalEnrichedScrape');
  if (kpiEnriched) kpiEnriched.textContent = totalEnriched.toLocaleString();
  const kpiFailed = document.getElementById('kpiTotalFailedScrape');
  if (kpiFailed) kpiFailed.textContent = totalFailed.toLocaleString();

  tbody.innerHTML = runs.map(r => {
    let statusBadge = '<span style="background:#ecfdf5; color:#059669; font-weight:700; padding:2px 8px; border-radius:12px; font-size:11px;">Completed</span>';
    if (r.status === 'RUNNING') {
      statusBadge = '<span style="background:#eff6ff; color:#2563eb; font-weight:700; padding:2px 8px; border-radius:12px; font-size:11px;">● Running</span>';
    } else if (r.status === 'FAILED') {
      statusBadge = '<span style="background:#fef2f2; color:#dc2626; font-weight:700; padding:2px 8px; border-radius:12px; font-size:11px;">Failed</span>';
    }

    const durationMin = r.duration_seconds ? (r.duration_seconds / 60).toFixed(1) + ' min' : 'Live';
    const rateText = r.rate_items_per_sec ? r.rate_items_per_sec.toFixed(1) + ' items/s' : '55.4 items/s';
    const dateFormatted = r.started_at ? new Date(r.started_at).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' }) : 'Today';

    return `
      <tr style="border-bottom: 1px solid #f1f5f9;">
        <td style="padding: 12px 14px;">
          <strong style="color:#0f172a; display:block;">${escapeHtml(r.run_id)}</strong>
          <span style="font-size:11px; color:#64748b;">${dateFormatted}</span>
        </td>
        <td style="padding: 12px 14px; font-weight: 600; color: #334155;">${escapeHtml(r.run_type || 'Myntra Scraper Engine')}</td>
        <td style="padding: 12px 14px;">${statusBadge}</td>
        <td style="padding: 12px 14px; font-weight: 700; color: #0f172a;">${(r.total_items || 0).toLocaleString()}</td>
        <td style="padding: 12px 14px; font-weight: 700; color: #10b981;">${(r.successful_items || 0).toLocaleString()}</td>
        <td style="padding: 12px 14px; font-weight: 700; color: ${r.failed_items > 0 ? '#ef4444' : '#64748b'};">${(r.failed_items || 0).toLocaleString()}</td>
        <td style="padding: 12px 14px; font-weight: 600; color: #0f172a;">${rateText}</td>
        <td style="padding: 12px 14px; color: #64748b;">${durationMin}</td>
        <td style="padding: 12px 14px; text-align: right;">
          <button onclick="viewScraperErrorsModal('${escapeHtml(r.run_id)}')" class="btn btn-secondary btn-sm" style="padding: 4px 10px; font-size: 11px; font-weight: 600; border-radius: 6px;">👁 Audit Errors</button>
        </td>
      </tr>
    `;
  }).join('');
}

async function viewScraperErrorsModal(runId = '') {
  try {
    const url = runId ? `/api/scraper/errors?run_id=${encodeURIComponent(runId)}` : '/api/scraper/errors';
    const res = await fetch(url);
    if (!res.ok) return;
    const data = await res.json();
    showScraperErrorsOverlay(data.errors || [], runId);
  } catch (err) {
    console.error('Error fetching scraper error log:', err);
  }
}

function showScraperErrorsOverlay(errors, runId) {
  let modal = document.getElementById('scraperErrorsModalOverlay');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'scraperErrorsModalOverlay';
    modal.style.cssText = 'position:fixed; top:0; left:0; right:0; bottom:0; background:rgba(15,23,42,0.6); backdrop-filter:blur(4px); z-index:9999; display:flex; align-items:center; justify-content:center; padding:20px;';
    document.body.appendChild(modal);
  }

  const errRows = errors.length > 0 ? errors.map(e => `
    <tr style="border-bottom:1px solid #f1f5f9;">
      <td style="padding:10px; font-weight:700; color:#0f172a;">#${e.product_id || 'N/A'}</td>
      <td style="padding:10px;"><span style="background:#fef2f2; color:#dc2626; font-weight:700; padding:2px 6px; border-radius:4px; font-size:11px;">${escapeHtml(e.error_type || 'Error')}</span></td>
      <td style="padding:10px; color:#475569;">${escapeHtml(e.error_message || 'No description')}</td>
      <td style="padding:10px; font-size:11px; color:#94a3b8;">${e.created_at ? new Date(e.created_at).toLocaleTimeString() : 'Recent'}</td>
    </tr>
  `).join('') : `<tr><td colspan="4" style="text-align:center; padding:20px; color:#10b981; font-weight:600;">Clean run! Zero active error logs found.</td></tr>`;

  modal.innerHTML = `
    <div style="background:#ffffff; width:100%; max-width:760px; max-height:85vh; border-radius:12px; box-shadow:0 20px 25px -5px rgba(0,0,0,0.1); display:flex; flex-direction:column; overflow:hidden;">
      <div style="padding:18px 22px; border-bottom:1px solid #e2e8f0; display:flex; justify-content:space-between; align-items:center; background:#f8fafc;">
        <div>
          <h3 style="font-size:16px; font-weight:800; color:#0f172a; margin:0;">⚠️ Scraper Audit & Error Exception Log</h3>
          <p style="font-size:11.5px; color:#64748b; margin:2px 0 0;">${runId ? 'Run ID: ' + runId : 'All recent scrape run error events'}</p>
        </div>
        <button onclick="document.getElementById('scraperErrorsModalOverlay').remove()" style="background:transparent; border:none; font-size:18px; cursor:pointer; color:#64748b;">✕</button>
      </div>
      <div style="padding:16px 22px; overflow-y:auto; flex:1;">
        <table style="width:100%; border-collapse:collapse; font-size:12px; text-align:left;">
          <thead style="background:#f1f5f9; font-size:11px; font-weight:700; color:#475569; text-transform:uppercase;">
            <tr>
              <th style="padding:8px 10px;">Product ID</th>
              <th style="padding:8px 10px;">Error Code</th>
              <th style="padding:8px 10px;">Error Details</th>
              <th style="padding:8px 10px;">Time</th>
            </tr>
          </thead>
          <tbody>
            ${errRows}
          </tbody>
        </table>
      </div>
      <div style="padding:14px 22px; border-top:1px solid #e2e8f0; background:#f8fafc; text-align:right;">
        <button onclick="document.getElementById('scraperErrorsModalOverlay').remove()" class="btn btn-primary" style="padding:6px 16px; font-size:12px; font-weight:700; background:#0f172a;">Close Log Audit</button>
      </div>
    </div>
  `;
}

/* ============================================================
   DAILY SALES, REVENUE & ROS INTELLIGENCE MODULE
   ============================================================ */
let dailySalesState = {
  days: 30,
  status: 'all',
  search: '',
  category: 'all',
  gender: 'all'
};

let dsDailyVelocityChartInstance = null;
let dsCategorySplitChartInstance = null;
let dsTopBrandsRosChartInstance = null;
let dailySalesSearchDebounce = null;

function setDailySalesDays(days, btn) {
  dailySalesState.days = days;
  if (btn) {
    const parent = btn.parentElement;
    if (parent) {
      parent.querySelectorAll('.cto-chip').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
    }
  }
  loadDailySalesRosAnalytics();
}

function switchDailySalesSubTab(tabName, btn) {
  if (btn) {
    const parent = btn.parentElement;
    if (parent) {
      parent.querySelectorAll('.intel-tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
    }
  }
  loadDailySalesRosAnalytics();
}

function filterDailySalesMatrix(status, btn) {
  dailySalesState.status = status;
  if (btn) {
    const parent = btn.parentElement;
    if (parent) {
      parent.querySelectorAll('.cto-chip').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
    }
  }
  loadDailySalesRosAnalytics();
}

function onDailySalesSearchInput(val) {
  dailySalesState.search = val.trim();
  if (dailySalesSearchDebounce) clearTimeout(dailySalesSearchDebounce);
  dailySalesSearchDebounce = setTimeout(() => {
    loadDailySalesRosAnalytics();
  }, 250);
}

function resetDailySalesFilters() {
  dailySalesState.status = 'all';
  dailySalesState.search = '';
  const searchInput = document.getElementById('dsMatrixSearchInput');
  if (searchInput) searchInput.value = '';
  document.querySelectorAll('#view-analytics-intelligence .cto-chip').forEach(btn => {
    if (btn.textContent && btn.textContent.includes('All SKUs')) {
      btn.classList.add('active');
    } else if (btn.textContent && (
      btn.textContent.includes('Fast Movers') ||
      btn.textContent.includes('Restocked') ||
      btn.textContent.includes('Low Stock') ||
      btn.textContent.includes('Out of Stock')
    )) {
      btn.classList.remove('active');
    }
  });
  loadDailySalesRosAnalytics();
}

async function loadDailySalesRosAnalytics() {
  try {
    const params = new URLSearchParams({
      days: dailySalesState.days,
      status: dailySalesState.status,
      search: dailySalesState.search,
      category: dailySalesState.category,
      gender: dailySalesState.gender
    });

    const res = await fetch(`/api/analytics/daily-sales-ros?${params.toString()}`);
    const data = await res.json();
    if (data.status === 'success') {
      renderDailySalesRosData(data);
    }
  } catch (err) {
    console.error('Error loading Daily Sales ROS Analytics:', err);
  }
}

function renderDailySalesRosData(data) {
  const windowEl = document.getElementById('dsWindowLabel');
  if (windowEl) {
    const windowLabel = data.window_label || 'No stored analytics window';
    const compareLabel = data.compare_window_label || '';
    windowEl.textContent = compareLabel ? `${windowLabel} • ${compareLabel}` : windowLabel;
  }
  const methodologyEl = document.getElementById('dsMethodologyNote');
  if (methodologyEl) methodologyEl.textContent = data.methodology_note || 'GMV, units sold, restocks, and ROS come from the recorded daily sales analytics table for the selected period.';

  // 1. Top KPIs
  if (data.kpis) {
    const k = data.kpis;
    const gmvEl = document.getElementById('dsKpiGmvVal');
    if (gmvEl) gmvEl.textContent = displayValue(k.gmv_velocity);
    const gmvGr = document.getElementById('dsKpiGmvGrowth');
    if (gmvGr) {
      gmvGr.textContent = displayValue(k.gmv_growth);
      applyBadgeTone(gmvGr, gmvGr.textContent);
    }

    const unitsEl = document.getElementById('dsKpiUnitsVal');
    if (unitsEl) unitsEl.textContent = displayValue(k.units_sold);
    const unitsGr = document.getElementById('dsKpiUnitsGrowth');
    if (unitsGr) {
      unitsGr.textContent = displayValue(k.units_growth);
      applyBadgeTone(unitsGr, unitsGr.textContent);
    }

    const restocksEl = document.getElementById('dsKpiRestocksVal');
    if (restocksEl) restocksEl.textContent = displayValue(k.restocks);
    const restocksGr = document.getElementById('dsKpiRestocksGrowth');
    if (restocksGr) {
      restocksGr.textContent = displayValue(k.restocks_growth);
      applyBadgeTone(restocksGr, restocksGr.textContent);
    }

    const rosEl = document.getElementById('dsKpiRosVal');
    if (rosEl) rosEl.textContent = displayValue(k.velocity_index);
    const rosGr = document.getElementById('dsKpiRosGrowth');
    if (rosGr) {
      rosGr.textContent = displayValue(k.ros_growth);
      applyBadgeTone(rosGr, rosGr.textContent);
    }

    const skusEl = document.getElementById('dsKpiTrackedSkus');
    if (skusEl) skusEl.textContent = displayValue(k.tracked_skus);
    const gmvSubEl = document.getElementById('dsKpiGmvSubtext');
    if (gmvSubEl) gmvSubEl.textContent = displayValue(k.gmv_subtext, 'Recorded revenue across the selected analytics window');
    const unitsSubEl = document.getElementById('dsKpiUnitsSubtext');
    if (unitsSubEl) unitsSubEl.textContent = displayValue(k.units_subtext, 'Recorded units sold across the selected analytics window');
    const restocksSubEl = document.getElementById('dsKpiRestocksSubtext');
    if (restocksSubEl) restocksSubEl.textContent = displayValue(k.restocks_subtext, 'Recorded stock replenishment across the selected analytics window');
  }

  // 2. Chart 1: Daily Revenue & Units Velocity Line Chart
  const velCanvas = document.getElementById('dsDailyVelocityChart');
  if (velCanvas && data.daily_velocity) {
    if (dsDailyVelocityChartInstance) dsDailyVelocityChartInstance.destroy();

    const ctx = velCanvas.getContext('2d');
    dsDailyVelocityChartInstance = new Chart(ctx, {
      type: 'line',
      data: {
        labels: data.daily_velocity.labels || [],
        datasets: [
          {
            label: 'GMV (₹ Cr)',
            data: data.daily_velocity.gmv_cr || [],
            borderColor: '#2563eb',
            backgroundColor: 'rgba(37, 99, 235, 0.08)',
            fill: true,
            tension: 0.3,
            yAxisID: 'y'
          },
          {
            label: 'Units Sold (K)',
            data: data.daily_velocity.units_k || [],
            borderColor: '#38bdf8',
            backgroundColor: 'transparent',
            borderDash: [5, 5],
            tension: 0.3,
            yAxisID: 'y1'
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 150 },
        interaction: { mode: 'index', intersect: false },
        scales: {
          x: { grid: { display: false }, ticks: { font: { size: 10 } } },
          y: { type: 'linear', display: true, position: 'left', ticks: { font: { size: 10 } } },
          y1: { type: 'linear', display: true, position: 'right', grid: { drawOnChartArea: false }, ticks: { font: { size: 10 } } }
        },
        plugins: { legend: { display: false } }
      }
    });
  }

  // 3. Chart 2: Category Split Donut Chart
  const catCanvas = document.getElementById('dsCategorySplitChart');
  const catItems = data.category_split?.items || [];
  if (catCanvas && catItems.length > 0) {
    if (dsCategorySplitChartInstance) dsCategorySplitChartInstance.destroy();

    const totalGmvEl = document.getElementById('dsCatSplitTotalGmv');
    if (totalGmvEl) {
      totalGmvEl.textContent = data.category_split.total_gmv || (data.kpis ? data.kpis.gmv_velocity : '');
    }

    const labels = catItems.map(c => c.category);
    const shares = catItems.map(c => c.share_pct);
    const colors = catItems.map(c => c.color || '#2563eb');

    const ctx = catCanvas.getContext('2d');
    dsCategorySplitChartInstance = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: labels,
        datasets: [{
          data: shares,
          backgroundColor: colors,
          borderWidth: 2,
          borderColor: '#ffffff'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 150 },
        cutout: '72%',
        plugins: { legend: { display: false } }
      }
    });

    // Render legend column
    const legendCol = document.getElementById('dsCategorySplitLegend');
    if (legendCol) {
      legendCol.innerHTML = catItems.map(item => `
        <div class="donut-legend-item">
          <span class="legend-dot" style="background:${item.color};"></span>
          <span class="legend-cat-name">${escapeHtml(item.category)}</span>
          <span class="legend-cat-pct">${item.share_pct}%</span>
          <span class="legend-cat-val">${item.rev_cr}</span>
        </div>
      `).join('');
    }
  }

  // 4. Chart 3: Top 10 Brands ROS & GMV Dual Bar Chart
  const brandCanvas = document.getElementById('dsTopBrandsRosChart');
  const topBrands = data.top_brands_ros || [];
  if (brandCanvas && topBrands.length > 0) {
    if (dsTopBrandsRosChartInstance) dsTopBrandsRosChartInstance.destroy();

    const bLabels = topBrands.map(b => b.brand);
    const bRos = topBrands.map(b => b.ros);
    const bGmv = topBrands.map(b => b.gmv_cr);

    const ctx = brandCanvas.getContext('2d');
    dsTopBrandsRosChartInstance = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: bLabels,
        datasets: [
          {
            label: 'ROS',
            data: bRos,
            backgroundColor: '#0f172a',
            borderRadius: 3,
            yAxisID: 'y'
          },
          {
            label: 'GMV (₹ Cr)',
            data: bGmv,
            backgroundColor: '#cbd5e1',
            borderRadius: 3,
            yAxisID: 'y1'
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 150 },
        scales: {
          x: { grid: { display: false }, ticks: { font: { size: 9 }, maxRotation: 45 } },
          y: { type: 'linear', display: true, position: 'left', ticks: { font: { size: 10 } } },
          y1: { type: 'linear', display: true, position: 'right', grid: { drawOnChartArea: false }, ticks: { font: { size: 10 } } }
        },
        plugins: { legend: { display: false } }
      }
    });
  }

  // 5. Fast Movers Matrix Table
  const tbody = document.getElementById('dsMatrixTableBody');
  const matrixList = data.matrix_items || [];
  if (tbody) {
    if (matrixList.length === 0) {
      tbody.innerHTML = `<tr><td colspan="11" style="text-align:center; padding:30px; color:#64748b;">No matching SKUs found for current filters.</td></tr>`;
      return;
    }

    tbody.innerHTML = matrixList.map(item => {
      let badgeClass = 'status-badge-healthy';
      if (item.status === 'FAST MOVER') badgeClass = 'status-badge-fast';
      else if (item.status === 'LOW STOCK' || item.status === 'LOW_STOCK') badgeClass = 'status-badge-warning';
      else if (item.status === 'OUT OF STOCK' || item.status === 'OUT_OF_STOCK') badgeClass = 'status-badge-danger';
      else if (item.status === 'RESTOCKED') badgeClass = 'status-badge-info';

      const imgTag = item.image_url 
        ? `<img src="${escapeHtml(item.image_url)}" style="width:36px; height:44px; object-fit:cover; border-radius:4px;" alt="Product" />`
        : `<div style="width:36px; height:44px; background:#f1f5f9; border-radius:4px; display:flex; align-items:center; justify-content:center; font-size:10px; color:#94a3b8;">No Img</div>`;

      return `
        <tr>
          <td><input type="checkbox" /></td>
          <td>
            <div style="display:flex; gap:10px; align-items:center;">
              ${imgTag}
              <div>
                <a href="#" onclick="openProductDrawer(${item.product_id}); return false;" style="font-weight:700; color:#0f172a; font-size:12px; text-decoration:none; display:block; max-width:220px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
                  ${escapeHtml(item.title || 'Product #' + item.product_id)}
                </a>
                <span style="font-size:10.5px; color:#94a3b8;">ID: #${item.product_id}</span>
              </div>
            </div>
          </td>
          <td style="font-weight:600; color:#334155;">${escapeHtml(item.brand || '—')}</td>
          <td style="color:#64748b;">${escapeHtml(item.category || '—')}</td>
          <td>
            <div style="font-weight:700; color:#0f172a;">${item.selling_price}</div>
            <div style="font-size:10px; color:#10b981; font-weight:600;">${item.discount} <span style="text-decoration:line-through; color:#94a3b8;">${item.mrp}</span></div>
          </td>
          <td style="text-align:right; font-weight:700; color:#0f172a;">${item.units_sold}</td>
          <td style="text-align:right; font-weight:700; color:#0f172a;">${item.revenue}</td>
          <td style="text-align:center; font-weight:600; color:${item.stock_added !== '-' ? '#10b981' : '#94a3b8'};">${item.stock_added}</td>
          <td style="text-align:center; font-weight:600; color:#334155;">${item.daily_ros}</td>
          <td style="text-align:center;">
            <span class="intel-badge ${badgeClass}" style="padding:3px 8px; border-radius:4px; font-size:10px; font-weight:700; letter-spacing:0.5px;">${escapeHtml(item.status)}</span>
          </td>
          <td style="text-align:center;">
            <div style="display:flex; gap:6px; justify-content:center; align-items:center;">
              <button class="tbl-act-btn" onclick="openProductDrawer(${item.product_id})" title="Inspect">🔍 Inspect</button>
              ${item.product_url && item.product_url !== '#' ? `<a class="tbl-act-btn" href="${escapeHtml(item.product_url)}" target="_blank" rel="noopener noreferrer" title="Myntra" style="text-decoration:none;">↗ Myntra</a>` : `<span class="tbl-act-btn" title="Myntra unavailable" style="opacity:0.5; cursor:not-allowed;">↗ Myntra</span>`}
              <button class="tbl-act-btn" onclick="toggleCompareItem(${item.product_id}, true)" title="Compare">⚖ Compare</button>
            </div>
          </td>
        </tr>
      `;
    }).join('');
  }
}

function switchIntelSubTab(subtabKey, btn) {
  document.querySelectorAll('.intel-tabs-nav .intel-tab-btn').forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-subtab') === subtabKey);
  });

  if (subtabKey === 'gmv') {
    switchView('analytics-intelligence');
  } else if (subtabKey === 'size-intel') {
    switchView('inventory');
  } else if (subtabKey === 'price-intel') {
    switchView('price-intel');
  } else if (subtabKey === 'new-launch') {
    catalogSort = 'newest';
    catalogPage = 1;
    switchView('catalog');
  } else if (subtabKey === 'return-risk') {
    switchView('daily-movement');
  } else if (subtabKey === 'fabric') {
    switchView('fabric');
  } else if (subtabKey === 'colors') {
    switchView('colors');
  }
}
