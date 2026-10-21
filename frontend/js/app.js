/**
 * EVENT INSIGHT - Frontend Application Logic
 * Integrates 3 Modules:
 * 1. Advanced Social/Text Media Analysis (Offline NLP Pipeline)
 * 2. IT Project Management (Project, Tasks Kanban, Milestones, Risks, Stakeholders)
 * 3. Enterprise System (RBAC Auth, Negative Sentiment Issue Ticketing & Workflows)
 */

const API_BASE = "http://localhost:8800";

// Global Application State
let selectedFile = null;
let ratingsChartInstance = null;
let currentAnalysisId = null;
let currentAnalysisData = null;
let selectedAnalysisId = null; // Analysis currently selected for distinct issues view
let selectedIssueId = null;    // Issue currently selected for single-issue focus detail view
let cachedIssuesList = [];
let cachedCategories = [];
let allAnalyses = [];
let currentUser = null; // { id, username, role }
let authToken = localStorage.getItem("event_insight_token") || null;

// DOM Elements - Navigation & Status
const navTabs = document.querySelectorAll(".header-nav .nav-tab");
const backendStatusBadge = document.getElementById("backendStatusBadge");
const authHeaderWidget = document.getElementById("authHeaderWidget");
const navIssuesBadge = document.getElementById("navIssuesBadge");
const themeToggleBtn = document.getElementById("themeToggleBtn");
const themeToggleIcon = document.getElementById("themeToggleIcon");

// Theme State (Default: light or saved in localStorage)
let currentTheme = localStorage.getItem("event_insight_theme") || "light";

function applyTheme(theme) {
  currentTheme = theme;
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem("event_insight_theme", theme);
  
  if (themeToggleIcon) {
    themeToggleIcon.setAttribute("data-lucide", theme === "dark" ? "sun" : "moon");
    if (window.lucide) lucide.createIcons();
  }

  // Re-render ratings chart if it exists to adapt grid/tick colors to current theme
  if (ratingsChartInstance && currentAnalysisData) {
    renderResults(currentAnalysisData);
  }
}

function initTheme() {
  applyTheme(currentTheme);
  if (themeToggleBtn) {
    themeToggleBtn.addEventListener("click", () => {
      const nextTheme = currentTheme === "dark" ? "light" : "dark";
      applyTheme(nextTheme);
    });
  }
}

// DOM Elements - Overview & Ingestion
const csvFileInput = document.getElementById("csvFile");
const dropzone = document.getElementById("dropzoneContainer");
const fileBadge = document.getElementById("fileSelectionBadge");
const eventNameInput = document.getElementById("eventName");
const analyzeBtn = document.getElementById("analyzeBtn");
const reportBtn = document.getElementById("reportBtn");
const statusEl = document.getElementById("status");
const resultsSection = document.getElementById("results");
const overviewResults = document.getElementById("overview-results");

// DOM Elements - Enterprise Trigger on Analysis
const enterpriseIssueTriggerCard = document.getElementById("enterpriseIssueTriggerCard");
const enterpriseTriggerDesc = document.getElementById("enterpriseTriggerDesc");
const triggerCreateIssuesBtn = document.getElementById("triggerCreateIssuesBtn");
const triggerCreateIssuesLabel = document.getElementById("triggerCreateIssuesLabel");
const enterpriseIssueTriggerMsg = document.getElementById("enterpriseIssueTriggerMsg");

// ==============================================================================
// 1. Initialization
// ==============================================================================

document.addEventListener("DOMContentLoaded", async () => {
  initTheme();

  if (window.lucide) {
    lucide.createIcons();
  }

  setupNavigation();
  setupModalHandlers();
  setupProjectSubTabs();

  // Check backend health & auth status
  checkBackendHealth();
  await checkAuthStatus();

  // Load initial data modules
  await fetchHistory();
  loadProjectData();
  loadTasks();
  loadMilestones();
  loadRisks();
  loadStakeholders();
  await loadCategories();
  loadIssues();
  loadIssueStats();
  initDatabaseModule();

  // Event Listeners
  const refreshHistoryBtn = document.getElementById("refreshHistoryBtn");
  if (refreshHistoryBtn) {
    refreshHistoryBtn.addEventListener("click", fetchHistory);
  }

  // Event Scope selector listener (keeps issues distinct for each event)
  const analysisScopeSelect = document.getElementById("filterIssueAnalysis");
  if (analysisScopeSelect) {
    analysisScopeSelect.addEventListener("change", (e) => {
      selectedAnalysisId = e.target.value ? parseInt(e.target.value) : null;
      selectedIssueId = null; // reset selected issue
      loadIssues();
      loadIssueStats();
    });
  }

  // Filter issue listeners
  const statusFilter = document.getElementById("filterIssueStatus");
  const priorityFilter = document.getElementById("filterIssuePriority");
  const categoryFilter = document.getElementById("filterIssueCategory");
  const resetFiltersBtn = document.getElementById("resetIssueFiltersBtn");

  if (statusFilter) statusFilter.addEventListener("change", loadIssues);
  if (priorityFilter) priorityFilter.addEventListener("change", loadIssues);
  if (categoryFilter) categoryFilter.addEventListener("change", loadIssues);
  if (resetFiltersBtn) {
    resetFiltersBtn.addEventListener("click", () => {
      if (statusFilter) statusFilter.value = "";
      if (priorityFilter) priorityFilter.value = "";
      if (categoryFilter) categoryFilter.value = "";
      loadIssues();
    });
  }

  // Enterprise trigger button
  if (triggerCreateIssuesBtn) {
    triggerCreateIssuesBtn.addEventListener("click", triggerCreateIssuesFromCurrentAnalysis);
  }

  // Form submission listeners
  setupFormSubmissions();
});

// ==============================================================================
// 2. Page Navigation & Tab Router (Clean SPA View Switching)
// ==============================================================================

let isNavClicking = false;
let navClickTimeout = null;

function setActiveNavTab(pageId) {
  navTabs.forEach(tab => {
    const p = tab.getAttribute("data-page");
    if (p === pageId) {
      tab.classList.add("active");
      // Keep active tab visible in horizontal scrolling header
      const container = tab.parentElement;
      if (container && container.classList.contains("header-nav")) {
        const tabLeft = tab.offsetLeft;
        const tabRight = tabLeft + tab.offsetWidth;
        if (tabLeft < container.scrollLeft) {
          container.scrollTo({ left: Math.max(0, tabLeft - 16), behavior: "smooth" });
        } else if (tabRight > container.scrollLeft + container.clientWidth) {
          container.scrollTo({ left: tabRight - container.clientWidth + 16, behavior: "smooth" });
        }
      }
    } else {
      tab.classList.remove("active");
    }
  });
}

function scrollToSection(pageId, updateHash = true) {
  const targetPage = document.getElementById(pageId);
  if (!targetPage) return;

  isNavClicking = true;
  setActiveNavTab(pageId);

  const headerOffset = 82;
  const elementPosition = targetPage.getBoundingClientRect().top;
  const offsetPosition = elementPosition + window.pageYOffset - headerOffset;

  window.scrollTo({
    top: Math.max(0, offsetPosition),
    behavior: "smooth"
  });

  if (updateHash) {
    history.replaceState(null, "", `#${pageId}`);
  }

  clearTimeout(navClickTimeout);
  navClickTimeout = setTimeout(() => {
    isNavClicking = false;
  }, 750);

  if (window.lucide) lucide.createIcons();
}

// Backward compatibility alias for any caller expecting switchPage
function switchPage(pageId, updateHash = true) {
  scrollToSection(pageId, updateHash);
}

function setupScrollSpy() {
  const navIds = Array.from(navTabs).map(t => t.getAttribute("data-page")).filter(Boolean);
  const sections = navIds.map(id => document.getElementById(id)).filter(Boolean);
  let scrollTicking = false;

  function onScroll() {
    if (isNavClicking) return;
    if (!scrollTicking) {
      window.requestAnimationFrame(() => {
        const scrollY = window.pageYOffset || document.documentElement.scrollTop;
        const headerOffset = 110;
        let currentId = navIds[0] || "overview";

        for (let i = 0; i < sections.length; i++) {
          const sec = sections[i];
          const top = sec.offsetTop - headerOffset;
          if (scrollY >= top - 25) {
            currentId = sec.id;
          }
        }

        // If at the very bottom of the page, activate the last section
        if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 60) {
          currentId = navIds[navIds.length - 1];
        }

        setActiveNavTab(currentId);
        scrollTicking = false;
      });
      scrollTicking = true;
    }
  }

  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", onScroll, { passive: true });
}

function setupNavigation() {
  navTabs.forEach(tab => {
    tab.addEventListener("click", (e) => {
      e.preventDefault();
      const pageId = tab.getAttribute("data-page");
      if (pageId) {
        scrollToSection(pageId);
      }
    });
  });

  // Handle direct URL hash or back/forward buttons
  window.addEventListener("hashchange", () => {
    const hash = window.location.hash.replace("#", "");
    if (hash && document.getElementById(hash)) {
      scrollToSection(hash, false);
    }
  });

  // Initial page from hash if available
  const initialHash = window.location.hash.replace("#", "");
  if (initialHash && document.getElementById(initialHash)) {
    setTimeout(() => scrollToSection(initialHash, false), 100);
  } else {
    setActiveNavTab("overview");
  }

  setupScrollSpy();
}

async function checkBackendHealth() {
  try {
    const res = await fetch(`${API_BASE}/api/health`);
    if (res.ok && backendStatusBadge) {
      backendStatusBadge.innerHTML = `<span class="status-pulse"></span><span>Online</span>`;
    }
  } catch (_) {
    if (backendStatusBadge) {
      backendStatusBadge.style.backgroundColor = "var(--neg-light)";
      backendStatusBadge.style.borderColor = "var(--neg-border)";
      backendStatusBadge.style.color = "var(--neg-text)";
      backendStatusBadge.innerHTML = `<span class="status-pulse" style="background:var(--neg);"></span><span>Offline</span>`;
    }
  }
}

// ==============================================================================
// 3. Authentication & RBAC (Enterprise System Subject)
// ==============================================================================

function getAuthHeaders(hasBody = true) {
  const headers = {};
  if (hasBody) {
    headers["Content-Type"] = "application/json";
  }
  if (authToken) {
    headers["Authorization"] = `Bearer ${authToken}`;
  }
  return headers;
}

async function checkAuthStatus() {
  if (!authToken) {
    currentUser = null;
    renderAuthUI();
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/api/auth/me`, {
      headers: { Authorization: `Bearer ${authToken}` }
    });
    if (res.ok) {
      currentUser = await res.json();
    } else {
      authToken = null;
      currentUser = null;
      localStorage.removeItem("event_insight_token");
    }
  } catch (_) {
    currentUser = null;
  }
  renderAuthUI();
}

function renderAuthUI() {
  if (!authHeaderWidget) return;

  if (currentUser) {
    const roleClass = currentUser.role === "admin" ? "admin" : "viewer";
    authHeaderWidget.innerHTML = `
      <div class="auth-user-pill">
        <i data-lucide="user" style="width:13px; height:13px;"></i>
        <span>${escapeHtml(currentUser.username)}</span>
        <span class="role-pill ${roleClass}">${currentUser.role}</span>
      </div>
      <button id="logoutBtn" class="btn btn-secondary btn-sm" title="Log out of system">
        <i data-lucide="log-out" style="width:13px; height:13px;"></i>
      </button>
    `;

    document.getElementById("logoutBtn")?.addEventListener("click", handleLogout);
  } else {
    authHeaderWidget.innerHTML = `
      <button id="headerLoginBtn" class="btn btn-primary btn-sm">
        <i data-lucide="log-in" style="width:13px; height:13px;"></i>
        <span>Sign In</span>
      </button>
    `;
    document.getElementById("headerLoginBtn")?.addEventListener("click", () => openModal("loginModal"));
  }

  // Update write button states based on admin privileges
  const isAdmin = currentUser?.role === "admin";
  document.querySelectorAll(".admin-only-btn").forEach(btn => {
    if (isAdmin) {
      btn.style.opacity = "1";
      btn.removeAttribute("disabled");
      btn.removeAttribute("title");
    } else {
      btn.style.opacity = "0.45";
      btn.setAttribute("disabled", "true");
      btn.setAttribute("title", "Admin authentication required to perform write actions");
    }
  });

  if (window.lucide) lucide.createIcons();
}

async function handleLogin(username, password) {
  const errorEl = document.getElementById("loginErrorMsg");
  const submitBtn = document.getElementById("loginSubmitBtn");
  if (errorEl) errorEl.style.display = "none";
  if (submitBtn) submitBtn.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password })
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Authentication failed");
    }

    const data = await res.json();
    authToken = data.access_token;
    currentUser = data.user;
    localStorage.setItem("event_insight_token", authToken);

    closeModal("loginModal");
    renderAuthUI();

    // Reload modules with updated permissions
    loadProjectData();
    loadTasks();
    loadMilestones();
    loadRisks();
    loadStakeholders();
    loadIssues();
  } catch (err) {
    if (errorEl) {
      errorEl.textContent = err.message;
      errorEl.style.display = "block";
    }
  } finally {
    if (submitBtn) submitBtn.disabled = false;
  }
}

function handleLogout() {
  authToken = null;
  currentUser = null;
  localStorage.removeItem("event_insight_token");
  renderAuthUI();

  // Reload views to refresh read-only indicators
  loadTasks();
  loadMilestones();
  loadRisks();
  loadStakeholders();
  loadIssues();
}

// ==============================================================================
// 4. Ingestion & NLP Analysis (Subject 1)
// ==============================================================================

function updateSelectedFileDisplay(file) {
  selectedFile = file || null;
  if (selectedFile) {
    fileBadge.style.display = "inline-flex";
    fileBadge.className = "selected-file-pill";
    fileBadge.innerHTML = `
      <i data-lucide="check"></i>
      <span>${escapeHtml(selectedFile.name)} (${(selectedFile.size / 1024).toFixed(1)} KB)</span>
    `;
  } else {
    fileBadge.style.display = "none";
    fileBadge.innerHTML = "";
  }
  if (window.lucide) lucide.createIcons();
}

if (csvFileInput) {
  csvFileInput.addEventListener("change", (e) => {
    updateSelectedFileDisplay(e.target.files[0] || null);
  });
}

if (dropzone) {
  ["dragenter", "dragover"].forEach(name => {
    dropzone.addEventListener(name, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.add("dragover");
    });
  });

  ["dragleave", "drop"].forEach(name => {
    dropzone.addEventListener(name, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.remove("dragover");
    });
  });

  dropzone.addEventListener("drop", (e) => {
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      const file = files[0];
      if (file.name.toLowerCase().endsWith(".csv")) {
        try {
          const dt = new DataTransfer();
          dt.items.add(file);
          csvFileInput.files = dt.files;
        } catch (_) {}
        updateSelectedFileDisplay(file);
      } else {
        statusEl.innerHTML = `
          <div class="alert alert-error">
            <i data-lucide="alert-circle"></i>
            <span>Please drop a valid .csv file exported from Google Forms.</span>
          </div>`;
        if (window.lucide) lucide.createIcons();
      }
    }
  });
}

// Sample Datasets 1-Click Loaders
async function loadSampleDataset(filename, defaultEventName) {
  try {
    statusEl.innerHTML = `
      <div class="alert alert-loading">
        <div class="spinner"></div>
        <span>Loading dataset ${escapeHtml(filename)}...</span>
      </div>`;
    if (window.lucide) lucide.createIcons();

    const res = await fetch(filename);
    if (!res.ok) throw new Error(`Could not fetch ${filename}`);
    const blob = await res.blob();
    const file = new File([blob], filename, { type: "text/csv" });

    try {
      const dt = new DataTransfer();
      dt.items.add(file);
      if (csvFileInput) csvFileInput.files = dt.files;
    } catch (_) {}

    updateSelectedFileDisplay(file);
    if (eventNameInput && defaultEventName) {
      eventNameInput.value = defaultEventName;
    }

    statusEl.innerHTML = `
      <div class="alert alert-success">
        <i data-lucide="check-circle-2"></i>
        <span>Dataset <strong>${escapeHtml(filename)}</strong> loaded! Click <em>Analyze Responses</em> to run.</span>
      </div>`;
    if (window.lucide) lucide.createIcons();
  } catch (err) {
    statusEl.innerHTML = `
      <div class="alert alert-error">
        <i data-lucide="alert-circle"></i>
        <span>Failed to load dataset: ${escapeHtml(err.message)}</span>
      </div>`;
    if (window.lucide) lucide.createIcons();
  }
}

const loadSample10Btn = document.getElementById("loadSample10Btn");
if (loadSample10Btn) {
  loadSample10Btn.addEventListener("click", () => {
    loadSampleDataset("sample_responses.csv", "College Tech Fest 2026");
  });
}

const loadSample100Btn = document.getElementById("loadSample100Btn");
if (loadSample100Btn) {
  loadSample100Btn.addEventListener("click", () => {
    loadSampleDataset("sample_100_responses.csv", "Annual College Symposium 2026");
  });
}

const loadSample500NegBtn = document.getElementById("loadSample500NegBtn");
if (loadSample500NegBtn) {
  loadSample500NegBtn.addEventListener("click", () => {
    loadSampleDataset("sample_500_negative_responses.csv", "Campus Symposium (Incident Review)");
  });
}

// Analyze Responses Action
if (analyzeBtn) {
  analyzeBtn.addEventListener("click", async () => {
    if (!selectedFile) {
      statusEl.innerHTML = `
        <div class="alert alert-error">
          <i data-lucide="alert-circle"></i>
          <span>Please select or drop a Google Forms CSV file first.</span>
        </div>`;
      if (window.lucide) lucide.createIcons();
      return;
    }

    statusEl.innerHTML = `
      <div class="alert alert-loading">
        <div class="spinner"></div>
        <span>Analyzing responses with local NLP pipeline...</span>
      </div>`;
    reportBtn.disabled = true;

    const formData = new FormData();
    formData.append("file", selectedFile);
    const eventName = eventNameInput?.value?.trim() || "Untitled Event";
    formData.append("event_name", eventName);

    try {
      const headers = {};
      if (authToken) headers["Authorization"] = `Bearer ${authToken}`;

      const res = await fetch(`${API_BASE}/api/analyze`, {
        method: "POST",
        headers,
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Server error (${res.status})`);
      }

      const data = await res.json();
      currentAnalysisId = data.id;
      currentAnalysisData = data;
      selectedAnalysisId = data.id; // Focus issues module on this newly analyzed event
      selectedIssueId = null;

      renderResults(data);
      await fetchHistory();
      loadIssues();
      loadIssueStats();

      statusEl.innerHTML = `
        <div class="alert alert-success">
          <i data-lucide="check-circle"></i>
          <span>Analysis complete! Processed ${data.total_responses} responses.</span>
        </div>`;
      reportBtn.disabled = false;

      const scrollTarget = document.getElementById("overview-results");
      if (scrollTarget) {
        scrollTarget.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    } catch (err) {
      statusEl.innerHTML = `
        <div class="alert alert-error">
          <i data-lucide="alert-circle"></i>
          <span>${escapeHtml(err.message)}. Ensure the backend is running at ${API_BASE}.</span>
        </div>`;
    } finally {
      if (window.lucide) lucide.createIcons();
    }
  });
}

// Download PDF Report Action
if (reportBtn) {
  reportBtn.addEventListener("click", async () => {
    const eventName = eventNameInput?.value || currentAnalysisData?.event_name || "College Event";
    if (!selectedFile && !currentAnalysisId) {
      alert("Please upload a CSV or load a saved analysis from history first.");
      return;
    }

    const prevHtml = reportBtn.innerHTML;
    reportBtn.innerHTML = `<div class="spinner"></div> Generating PDF...`;
    reportBtn.disabled = true;

    try {
      let res;
      if (currentAnalysisId) {
        res = await fetch(`${API_BASE}/api/analyses/${currentAnalysisId}/report`);
      } else {
        const formData = new FormData();
        formData.append("file", selectedFile);
        formData.append("event_name", eventName);
        res = await fetch(`${API_BASE}/api/report`, { method: "POST", body: formData });
      }
      if (!res.ok) throw new Error("Failed to generate PDF report.");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${eventName.replace(/\s+/g, "_")}_feedback_report.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      alert("Failed to generate PDF report. Please check the backend connection.");
    } finally {
      reportBtn.innerHTML = prevHtml;
      reportBtn.disabled = false;
      if (window.lucide) lucide.createIcons();
    }
  });
}

// Render Results Data onto Dashboard
function renderResults(data) {
  if (overviewResults) overviewResults.classList.remove("hidden");
  if (resultsSection) resultsSection.classList.remove("hidden");

  // Total Responses
  document.getElementById("totalResponses").textContent = data.total_responses;

  // Average Sentiment in Overview & Detail
  const avgSent = data.sentiment.average_compound;
  const avgSentOvEl = document.getElementById("avgSentimentOverview");
  if (avgSentOvEl) avgSentOvEl.textContent = avgSent;
  document.getElementById("avgSentiment").textContent = avgSent;

  // Dominant Sentiment Badge
  const domEl = document.getElementById("dominantSentiment");
  if (domEl) {
    if (avgSent >= 0.05) {
      domEl.textContent = "Positive";
      domEl.style.color = "var(--pos)";
    } else if (avgSent <= -0.05) {
      domEl.textContent = "Negative";
      domEl.style.color = "var(--neg)";
    } else {
      domEl.textContent = "Neutral";
      domEl.style.color = "var(--neu)";
    }
  }

  // Sentiment Breakdown Bar & Legend
  const { positive, neutral, negative } = data.sentiment;
  const total = Math.max(positive + neutral + negative, 1);
  const posPct = ((positive / total) * 100).toFixed(1);
  const neuPct = ((neutral / total) * 100).toFixed(1);
  const negPct = ((negative / total) * 100).toFixed(1);

  const bar = document.getElementById("sentimentBar");
  if (bar) {
    bar.innerHTML = `
      <div style="width:${posPct}%; background:var(--pos)" title="Positive: ${positive} (${posPct}%)">${positive > 0 ? positive : ''}</div>
      <div style="width:${neuPct}%; background:var(--neu)" title="Neutral: ${neutral} (${neuPct}%)">${neutral > 0 ? neutral : ''}</div>
      <div style="width:${negPct}%; background:var(--neg)" title="Negative: ${negative} (${negPct}%)">${negative > 0 ? negative : ''}</div>
    `;
  }

  const posLeg = document.getElementById("legendPosVal");
  const neuLeg = document.getElementById("legendNeuVal");
  const negLeg = document.getElementById("legendNegVal");
  if (posLeg) posLeg.textContent = `${positive} (${posPct}%)`;
  if (neuLeg) neuLeg.textContent = `${neutral} (${neuPct}%)`;
  if (negLeg) negLeg.textContent = `${negative} (${negPct}%)`;

  // Ratings Chart
  const ratingEntries = Object.entries(data.ratings || {});
  const ctx = document.getElementById("ratingsChart");
  if (ratingsChartInstance) ratingsChartInstance.destroy();

  if (ctx && ratingEntries.length > 0) {
    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    const gridColor = isDark ? "rgba(255, 255, 255, 0.08)" : "#e2e8f0";
    const tickColor = isDark ? "#94a3b8" : "#64748b";
    const barColor = isDark ? "#818cf8" : "#4f46e5";
    const barHover = isDark ? "#a5b4fc" : "#4338ca";

    ratingsChartInstance = new Chart(ctx, {
      type: "bar",
      data: {
        labels: ratingEntries.map(([k]) => k.length > 45 ? k.slice(0, 45) + "…" : k),
        datasets: [{
          label: "Average Rating",
          data: ratingEntries.map(([, v]) => v.average),
          backgroundColor: barColor,
          hoverBackgroundColor: barHover,
          borderRadius: 8,
          borderSkipped: false,
          maxBarThickness: 48
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: isDark ? "#1e293b" : "#0f172a",
            titleFont: { family: "'Plus Jakarta Sans', sans-serif", size: 13, weight: "700" },
            bodyFont: { family: "'Plus Jakarta Sans', sans-serif", size: 12, weight: "500" },
            borderColor: isDark ? "rgba(255,255,255,0.1)" : "transparent",
            borderWidth: 1,
            padding: 12,
            cornerRadius: 10
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            grid: { color: gridColor },
            ticks: { font: { family: "'Plus Jakarta Sans', sans-serif", weight: "500" }, color: tickColor }
          },
          x: {
            grid: { display: false },
            ticks: { font: { family: "'Plus Jakarta Sans', sans-serif", weight: "500" }, color: tickColor }
          }
        }
      }
    });
  }

  // Keywords
  const kwEl = document.getElementById("keywordsList");
  if (kwEl) {
    kwEl.innerHTML = (data.keywords || []).slice(0, 25)
      .map(k => `
        <span class="cloud-badge">
          <span>${escapeHtml(k.term)}</span>
          <span class="freq">${k.score}</span>
        </span>
      `).join("") || `<span style="font-size:0.85rem; color:var(--text-muted);">No significant keywords extracted.</span>`;
  }

  // Topics
  const topicsEl = document.getElementById("topics");
  if (topicsEl) {
    topicsEl.innerHTML = (data.topics || [])
      .map(t => `
        <div class="topic-card">
          <span class="topic-badge">Topic ${t.topic}</span>
          <div class="topic-content">
            <strong>Keywords:</strong> ${t.keywords.map(w => escapeHtml(w)).join(", ")}
          </div>
        </div>
      `).join("") || `<div style="font-size:0.85rem; color:var(--text-muted); font-style:italic;">Not enough text data to cluster topics.</div>`;
  }

  // Word Cloud
  const wcEl = document.getElementById("wordcloudImg");
  const wcPlaceholder = document.getElementById("wordcloudPlaceholder");
  if (wcEl) {
    if (data.wordcloud_image) {
      wcEl.src = `data:image/png;base64,${data.wordcloud_image}`;
      wcEl.style.display = "block";
      if (wcPlaceholder) wcPlaceholder.style.display = "none";
    } else {
      wcEl.style.display = "none";
      if (wcPlaceholder) wcPlaceholder.style.display = "block";
    }
  }

  // Summary
  const summaryEl = document.getElementById("summary");
  if (summaryEl) {
    summaryEl.textContent = data.ai_summary || "No free-text feedback was provided.";
  }

  // Update Enterprise Issue Trigger Card with Negatives Count
  updateEnterpriseTriggerCard(data);

  if (window.lucide) lucide.createIcons();
}

function updateEnterpriseTriggerCard(data) {
  if (!enterpriseIssueTriggerCard) return;

  const perResponse = data?.sentiment?.per_response || [];
  const negativeCount = perResponse.filter(r => (r.compound || 0) <= -0.30).length;

  if (enterpriseTriggerDesc) {
    enterpriseTriggerDesc.innerHTML = `
      Detected <strong>${negativeCount}</strong> student remarks with negative sentiment (compound polarity &le; -0.30)
      in <em>${escapeHtml(data.event_name || "this event")}</em>.
      Convert these automatically into categorized Enterprise Issues with department dispatching.
    `;
  }

  if (triggerCreateIssuesLabel) {
    triggerCreateIssuesLabel.textContent = negativeCount > 0
      ? `Generate ${negativeCount} Issues from this Analysis`
      : `Scan & Generate Issues from this Analysis`;
  }

  if (enterpriseIssueTriggerMsg) {
    enterpriseIssueTriggerMsg.style.display = "none";
    enterpriseIssueTriggerMsg.innerHTML = "";
  }
}

async function triggerCreateIssuesFromCurrentAnalysis() {
  if (!currentAnalysisId) {
    alert("Please select or run an analysis first.");
    return;
  }

  if (!currentUser) {
    openModal("loginModal");
    return;
  }

  if (currentUser.role !== "admin") {
    alert("Administrator privileges are required to generate issues.");
    return;
  }

  const prevText = triggerCreateIssuesBtn.innerHTML;
  triggerCreateIssuesBtn.innerHTML = `<div class="spinner"></div> Generating Tickets...`;
  triggerCreateIssuesBtn.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/api/analyses/${currentAnalysisId}/create-issues?threshold=-0.30`, {
      method: "POST",
      headers: getAuthHeaders(false),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to generate enterprise issues.");
    }

    const result = await res.json();

    if (enterpriseIssueTriggerMsg) {
      enterpriseIssueTriggerMsg.style.display = "block";
      enterpriseIssueTriggerMsg.innerHTML = `
        <div class="alert alert-success" style="margin-top: 0.5rem;">
          <i data-lucide="check-circle"></i>
          <span>Generated <strong>${result.created_count}</strong> distinct issue tickets (${result.skipped_duplicates} duplicate items skipped).</span>
        </div>
      `;
    }

    // Ensure issues module scopes to this analysis
    selectedAnalysisId = currentAnalysisId;
    selectedIssueId = null;
    const scopeSel = document.getElementById("filterIssueAnalysis");
    if (scopeSel) scopeSel.value = selectedAnalysisId;

    loadIssues();
    loadIssueStats();

    // Scroll smoothly to Issues section
    setTimeout(() => {
      const issuesSection = document.getElementById("issues");
      if (issuesSection) {
        issuesSection.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    }, 600);
  } catch (err) {
    if (enterpriseIssueTriggerMsg) {
      enterpriseIssueTriggerMsg.style.display = "block";
      enterpriseIssueTriggerMsg.innerHTML = `
        <div class="alert alert-error" style="margin-top: 0.5rem;">
          <i data-lucide="alert-circle"></i>
          <span>${escapeHtml(err.message)}</span>
        </div>
      `;
    }
  } finally {
    triggerCreateIssuesBtn.innerHTML = prevText;
    triggerCreateIssuesBtn.disabled = false;
    if (window.lucide) lucide.createIcons();
  }
}

// ==============================================================================
// 5. Past Analyses (History) & Event Scoping
// ==============================================================================

async function fetchHistory() {
  const container = document.getElementById("historyListContainer");

  try {
    const res = await fetch(`${API_BASE}/api/history`);
    if (!res.ok) throw new Error("Could not fetch history");
    const items = await res.json();
    allAnalyses = items;

    // Populate the Event Scope selector in Issues module
    populateAnalysisScopeDropdown(items);

    if (container) renderHistoryList(items);
  } catch (err) {
    if (container) {
      container.innerHTML = `
        <div style="text-align: center; padding: 1.5rem; color: var(--neg); font-size: 0.85rem;">
          Failed to load past analyses. Ensure the backend is online at ${API_BASE}.
        </div>`;
    }
  }
}

function populateAnalysisScopeDropdown(items) {
  const select = document.getElementById("filterIssueAnalysis");
  if (!select) return;

  if (!items || items.length === 0) {
    select.innerHTML = `<option value="">No events recorded yet</option>`;
    return;
  }

  // Default selected analysis to currently active or newest
  if (!selectedAnalysisId && items.length > 0) {
    selectedAnalysisId = currentAnalysisId || items[0].id;
  }

  select.innerHTML = items.map(item => `
    <option value="${item.id}" ${item.id === selectedAnalysisId ? 'selected' : ''}>
      ${escapeHtml(item.event_name)} (#${item.id} &bull; ${item.total_responses} responses)
    </option>
  `).join("");

  select.value = selectedAnalysisId;
}

function renderHistoryList(items) {
  const container = document.getElementById("historyListContainer");
  if (!container) return;

  if (!items || items.length === 0) {
    container.innerHTML = `
      <div style="text-align: center; padding: 2.5rem 1rem; color: var(--text-muted); background: var(--bg-hover); border-radius: var(--radius-md); border: 1px dashed var(--border-color);">
        <i data-lucide="inbox" style="width: 32px; height: 32px; stroke-width: 1.5; margin-bottom: 0.5rem; opacity: 0.6; display: inline-block;"></i>
        <div style="font-weight: 600; font-size: 0.9rem; color: var(--text-main); margin-bottom: 0.25rem;">No Past Analyses Saved</div>
        <div style="font-size: 0.8rem;">Upload and analyze a CSV above to automatically archive your feedback reports here.</div>
      </div>`;
    if (window.lucide) lucide.createIcons();
    return;
  }

  const isAdmin = currentUser?.role === "admin";

  container.innerHTML = items.map(item => `
    <div class="history-item" style="display: flex; align-items: center; justify-content: space-between; padding: 0.85rem 1rem; border: 1px solid var(--border-color); border-radius: var(--radius-md); margin-bottom: 0.65rem; background: var(--bg-surface); gap: 1rem; transition: background-color 0.15s ease;">
      <div style="display: flex; align-items: center; gap: 0.85rem; min-width: 0; flex: 1; cursor: pointer;" class="history-load-trigger" data-id="${item.id}" title="Click to reload this report">
        <div style="width: 38px; height: 38px; border-radius: var(--radius-md); background: var(--primary-light); color: var(--primary); display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
          <i data-lucide="file-bar-chart" style="width: 18px; height: 18px;"></i>
        </div>
        <div style="min-width: 0;">
          <div style="font-weight: 600; font-size: 0.92rem; color: var(--text-main); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
            ${escapeHtml(item.event_name)}
          </div>
          <div style="font-size: 0.76rem; color: var(--text-muted); display: flex; align-items: center; gap: 0.75rem; margin-top: 2px;">
            <span style="display: inline-flex; align-items: center; gap: 4px;"><i data-lucide="calendar" style="width: 12px; height: 12px;"></i> ${escapeHtml(item.uploaded_at)}</span>
            <span>&bull;</span>
            <span style="display: inline-flex; align-items: center; gap: 4px;"><i data-lucide="users" style="width: 12px; height: 12px;"></i> ${item.total_responses} responses</span>
          </div>
        </div>
      </div>
      <div style="display: flex; align-items: center; gap: 0.5rem; flex-shrink: 0;">
        <button class="btn btn-primary btn-sm history-load-btn" data-id="${item.id}" title="Reload this analysis into dashboard">
          <i data-lucide="eye"></i>
          <span>Load</span>
        </button>
        <a href="${API_BASE}/api/analyses/${item.id}/report" target="_blank" download="${escapeHtml(item.event_name.replace(/\s+/g, '_'))}_report.pdf" class="btn btn-secondary btn-sm" title="Download PDF report" style="text-decoration: none; display: inline-flex; align-items: center; gap: 4px;">
          <i data-lucide="download"></i>
          <span>PDF</span>
        </a>
        ${isAdmin ? `
          <button class="btn btn-secondary btn-sm history-delete-btn" data-id="${item.id}" data-name="${escapeHtml(item.event_name)}" title="Delete analysis" style="color: var(--neg);">
            <i data-lucide="trash-2"></i>
          </button>
        ` : ''}
      </div>
    </div>
  `).join("");

  if (window.lucide) lucide.createIcons();

  container.querySelectorAll(".history-load-trigger, .history-load-btn").forEach(el => {
    el.addEventListener("click", (e) => {
      e.stopPropagation();
      const id = el.dataset.id;
      if (id) loadAnalysisFromHistory(id);
    });
  });

  container.querySelectorAll(".history-delete-btn").forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const id = btn.dataset.id;
      const name = btn.dataset.name || "this analysis";
      deleteAnalysisFromHistory(id, name);
    });
  });
}

async function loadAnalysisFromHistory(id) {
  statusEl.innerHTML = `
    <div class="alert alert-loading">
      <div class="spinner"></div>
      <span>Loading saved analysis #${id}...</span>
    </div>`;
  if (window.lucide) lucide.createIcons();

  try {
    const res = await fetch(`${API_BASE}/api/history/${id}`);
    if (!res.ok) throw new Error(`Failed to load analysis (${res.status})`);
    const data = await res.json();

    currentAnalysisId = data.id;
    currentAnalysisData = data;
    selectedAnalysisId = data.id; // Also select this analysis in Issues view
    selectedIssueId = null;

    const scopeSel = document.getElementById("filterIssueAnalysis");
    if (scopeSel) scopeSel.value = data.id;

    if (data.event_name && eventNameInput) {
      eventNameInput.value = data.event_name;
    }

    renderResults(data);
    loadIssues();
    loadIssueStats();

    statusEl.innerHTML = `
      <div class="alert alert-success">
        <i data-lucide="check-circle"></i>
        <span>Loaded past analysis: <strong>${escapeHtml(data.event_name || `Analysis #${id}`)}</strong> (${data.total_responses} responses).</span>
      </div>`;

    const scrollTarget = document.getElementById("overview-results");
    if (scrollTarget) {
      scrollTarget.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  } catch (err) {
    statusEl.innerHTML = `
      <div class="alert alert-error">
        <i data-lucide="alert-circle"></i>
        <span>${escapeHtml(err.message)}</span>
      </div>`;
  } finally {
    if (window.lucide) lucide.createIcons();
  }
}

async function deleteAnalysisFromHistory(id, name) {
  if (!confirm(`Are you sure you want to delete analysis for "${name}"?`)) return;

  try {
    const res = await fetch(`${API_BASE}/api/history/${id}`, {
      method: "DELETE",
      headers: getAuthHeaders(false),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to delete analysis");
    }
    fetchHistory();
  } catch (err) {
    alert(`Could not delete analysis: ${err.message}`);
  }
}

// ==============================================================================
// 6. IT Project Management Module (Subject 2)
// ==============================================================================

function setupProjectSubTabs() {
  const tabs = document.querySelectorAll(".project-subtab");
  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      const targetId = tab.dataset.target;
      tabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");

      document.querySelectorAll(".project-subview").forEach(view => {
        view.classList.remove("active");
        if (view.id === targetId) view.classList.add("active");
      });
    });
  });
}

async function loadProjectData() {
  try {
    const res = await fetch(`${API_BASE}/api/project`);
    if (!res.ok) return;
    const proj = await res.json();

    const titleEl = document.getElementById("projectTitle");
    const descEl = document.getElementById("projectDesc");
    const datesEl = document.getElementById("projectDates");
    const statusBadge = document.getElementById("projectStatusBadge");

    if (titleEl) titleEl.textContent = proj.name;
    if (descEl) descEl.textContent = proj.description || "Annual feedback collection initiative.";
    if (datesEl) datesEl.textContent = `${proj.start_date} → ${proj.end_date}`;
    if (statusBadge) {
      statusBadge.textContent = proj.status;
      statusBadge.className = `status-badge ${proj.status.toLowerCase()}`;
    }

    // Prefill edit form
    const editName = document.getElementById("projEditName");
    const editStart = document.getElementById("projEditStartDate");
    const editEnd = document.getElementById("projEditEndDate");
    const editStatus = document.getElementById("projEditStatus");
    const editDesc = document.getElementById("projEditDesc");
    if (editName) editName.value = proj.name;
    if (editStart) editStart.value = proj.start_date;
    if (editEnd) editEnd.value = proj.end_date;
    if (editStatus) editStatus.value = proj.status;
    if (editDesc) editDesc.value = proj.description || "";

    // Stats
    const stats = proj.stats || {};
    const tasksDoneEl = document.getElementById("pmTasksDone");
    const tasksTotalEl = document.getElementById("pmTasksTotal");
    const taskBar = document.getElementById("pmTaskProgressBar");
    if (tasksDoneEl) tasksDoneEl.textContent = stats.completed_tasks || 0;
    if (tasksTotalEl) tasksTotalEl.textContent = `/ ${stats.total_tasks || 0} done`;
    if (taskBar) taskBar.style.width = `${stats.task_completion_pct || 0}%`;

    const msDoneEl = document.getElementById("pmMilestonesDone");
    const msTotalEl = document.getElementById("pmMilestonesTotal");
    const msBar = document.getElementById("pmMilestoneProgressBar");
    if (msDoneEl) msDoneEl.textContent = stats.completed_milestones || 0;
    if (msTotalEl) msTotalEl.textContent = `/ ${stats.total_milestones || 0} done`;
    if (msBar) msBar.style.width = `${stats.milestone_completion_pct || 0}%`;

    const risksEl = document.getElementById("pmOpenRisks");
    if (risksEl) risksEl.textContent = stats.open_risks || 0;

    const shEl = document.getElementById("pmStakeholdersCount");
    if (shEl) shEl.textContent = stats.total_stakeholders || 0;
  } catch (err) {
    console.error("Failed to load project details:", err);
  }
}

// Tasks Kanban
async function loadTasks() {
  try {
    const res = await fetch(`${API_BASE}/api/tasks`);
    if (!res.ok) return;
    const tasks = await res.json();

    const todoCards = document.getElementById("kanbanCardsTodo");
    const inProgCards = document.getElementById("kanbanCardsInProgress");
    const doneCards = document.getElementById("kanbanCardsDone");
    const countTodo = document.getElementById("countTodo");
    const countInProg = document.getElementById("countInProgress");
    const countDone = document.getElementById("countDone");

    if (!todoCards || !inProgCards || !doneCards) return;

    const todoList = tasks.filter(t => t.status === "todo");
    const inProgList = tasks.filter(t => t.status === "in-progress");
    const doneList = tasks.filter(t => t.status === "done");

    if (countTodo) countTodo.textContent = todoList.length;
    if (countInProg) countInProg.textContent = inProgList.length;
    if (countDone) countDone.textContent = doneList.length;

    todoCards.innerHTML = todoList.map(t => renderKanbanCard(t)).join("") || emptyKanbanColHtml();
    inProgCards.innerHTML = inProgList.map(t => renderKanbanCard(t)).join("") || emptyKanbanColHtml();
    doneCards.innerHTML = doneList.map(t => renderKanbanCard(t)).join("") || emptyKanbanColHtml();

    attachTaskCardListeners();
    if (window.lucide) lucide.createIcons();
  } catch (err) {
    console.error("Failed to load tasks:", err);
  }
}

function emptyKanbanColHtml() {
  return `<div style="text-align:center; padding: 1.5rem 0.5rem; color: var(--text-light); font-size: 0.78rem;">No tasks</div>`;
}

function renderKanbanCard(task) {
  const isAdmin = currentUser?.role === "admin";
  return `
    <div class="kanban-card" data-id="${task.id}">
      <div class="kanban-card-title">${escapeHtml(task.title)}</div>
      <div class="kanban-card-meta">
        <span><i data-lucide="user" style="width:11px; height:11px; display:inline;"></i> ${escapeHtml(task.assigned_to || "Unassigned")}</span>
        ${task.due_date ? `<span><i data-lucide="calendar" style="width:11px; height:11px; display:inline;"></i> ${escapeHtml(task.due_date)}</span>` : ''}
      </div>
      ${isAdmin ? `
        <div class="kanban-card-actions">
          ${task.status !== "todo" ? `<button class="kanban-action-btn move-task-btn" data-id="${task.id}" data-status="todo" title="Move to To Do">&larr; Todo</button>` : ''}
          ${task.status !== "in-progress" ? `<button class="kanban-action-btn move-task-btn" data-id="${task.id}" data-status="in-progress" title="Move to In Progress">In Prog</button>` : ''}
          ${task.status !== "done" ? `<button class="kanban-action-btn move-task-btn" data-id="${task.id}" data-status="done" title="Mark Done">Done &rarr;</button>` : ''}
          <button class="kanban-action-btn delete-task-btn" data-id="${task.id}" style="color:var(--neg); margin-left:auto;" title="Delete task">&times;</button>
        </div>
      ` : ''}
    </div>
  `;
}

function attachTaskCardListeners() {
  document.querySelectorAll(".move-task-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      const id = btn.dataset.id;
      const status = btn.dataset.status;
      try {
        const res = await fetch(`${API_BASE}/api/tasks/${id}`, {
          method: "PATCH",
          headers: getAuthHeaders(true),
          body: JSON.stringify({ status })
        });
        if (!res.ok) throw new Error("Failed to move task");
        loadTasks();
        loadProjectData();
      } catch (err) {
        alert(err.message);
      }
    });
  });

  document.querySelectorAll(".delete-task-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      if (!confirm("Delete this task?")) return;
      const id = btn.dataset.id;
      try {
        const res = await fetch(`${API_BASE}/api/tasks/${id}`, {
          method: "DELETE",
          headers: getAuthHeaders(false)
        });
        if (!res.ok) throw new Error("Failed to delete task");
        loadTasks();
        loadProjectData();
      } catch (err) {
        alert(err.message);
      }
    });
  });
}

// Milestones Timeline
async function loadMilestones() {
  const container = document.getElementById("milestonesListContainer");
  if (!container) return;

  try {
    const res = await fetch(`${API_BASE}/api/milestones`);
    if (!res.ok) return;
    const milestones = await res.json();

    if (milestones.length === 0) {
      container.innerHTML = `<div style="text-align:center; padding:2rem; color:var(--text-muted); font-size:0.85rem;">No milestones scheduled yet.</div>`;
      return;
    }

    const isAdmin = currentUser?.role === "admin";

    container.innerHTML = milestones.map(m => `
      <div class="milestone-item ${m.completed ? 'completed' : ''}">
        <div class="milestone-item-left">
          <input
            type="checkbox"
            class="milestone-checkbox"
            data-id="${m.id}"
            ${m.completed ? 'checked' : ''}
            ${!isAdmin ? 'disabled' : ''}
            title="${isAdmin ? 'Click to toggle completion' : 'Admin only'}"
          />
          <div>
            <div class="milestone-title">${escapeHtml(m.title)}</div>
            <div style="font-size:0.75rem; color:var(--text-muted); margin-top:2px;">
              <i data-lucide="calendar" style="width:11px; height:11px; display:inline;"></i> Target: ${escapeHtml(m.target_date)}
            </div>
          </div>
        </div>
        <div style="display:flex; align-items:center; gap:0.6rem;">
          <span class="badge-pill ${m.completed ? 'low' : 'medium'}">
            ${m.completed ? 'Completed' : 'Scheduled'}
          </span>
          ${isAdmin ? `
            <button class="btn btn-secondary btn-sm delete-milestone-btn" data-id="${m.id}" title="Delete milestone" style="color:var(--neg); padding:2px 6px;">
              <i data-lucide="trash-2" style="width:12px; height:12px;"></i>
            </button>
          ` : ''}
        </div>
      </div>
    `).join("");

    if (window.lucide) lucide.createIcons();

    // Toggle listener
    container.querySelectorAll(".milestone-checkbox").forEach(chk => {
      chk.addEventListener("change", async () => {
        const id = chk.dataset.id;
        const completed = chk.checked;
        try {
          const res = await fetch(`${API_BASE}/api/milestones/${id}`, {
            method: "PATCH",
            headers: getAuthHeaders(true),
            body: JSON.stringify({ completed })
          });
          if (!res.ok) throw new Error("Failed to update milestone");
          loadMilestones();
          loadProjectData();
        } catch (err) {
          alert(err.message);
          chk.checked = !completed;
        }
      });
    });

    // Delete listener
    container.querySelectorAll(".delete-milestone-btn").forEach(btn => {
      btn.addEventListener("click", async () => {
        if (!confirm("Delete this milestone?")) return;
        const id = btn.dataset.id;
        try {
          const res = await fetch(`${API_BASE}/api/milestones/${id}`, {
            method: "DELETE",
            headers: getAuthHeaders(false)
          });
          if (!res.ok) throw new Error("Failed to delete milestone");
          loadMilestones();
          loadProjectData();
        } catch (err) {
          alert(err.message);
        }
      });
    });
  } catch (err) {
    console.error("Failed to load milestones:", err);
  }
}

// Risks Register
async function loadRisks() {
  const tbody = document.getElementById("risksTableBody");
  if (!tbody) return;

  try {
    const res = await fetch(`${API_BASE}/api/risks`);
    if (!res.ok) return;
    const risks = await res.json();

    if (risks.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:2rem; color:var(--text-muted);">No risks registered.</td></tr>`;
      return;
    }

    const isAdmin = currentUser?.role === "admin";

    tbody.innerHTML = risks.map(r => `
      <tr>
        <td style="font-weight: 500;">${escapeHtml(r.description)}</td>
        <td><span class="badge-pill ${r.likelihood.toLowerCase()}">${r.likelihood}</span></td>
        <td><span class="badge-pill ${r.impact.toLowerCase()}">${r.impact}</span></td>
        <td style="font-size:0.8rem; color:var(--text-muted);">${escapeHtml(r.mitigation)}</td>
        <td><span class="badge-pill ${r.status.toLowerCase()}">${r.status}</span></td>
        <td style="text-align: right;">
          ${isAdmin ? `
            <button class="btn btn-secondary btn-sm delete-risk-btn" data-id="${r.id}" title="Delete risk" style="color:var(--neg); padding:2px 6px;">
              <i data-lucide="trash-2" style="width:12px; height:12px;"></i>
            </button>
          ` : '<span style="font-size:0.75rem; color:var(--text-light);">-</span>'}
        </td>
      </tr>
    `).join("");

    if (window.lucide) lucide.createIcons();

    tbody.querySelectorAll(".delete-risk-btn").forEach(btn => {
      btn.addEventListener("click", async () => {
        if (!confirm("Delete this risk entry?")) return;
        const id = btn.dataset.id;
        try {
          const res = await fetch(`${API_BASE}/api/risks/${id}`, {
            method: "DELETE",
            headers: getAuthHeaders(false)
          });
          if (!res.ok) throw new Error("Failed to delete risk");
          loadRisks();
          loadProjectData();
        } catch (err) {
          alert(err.message);
        }
      });
    });
  } catch (err) {
    console.error("Failed to load risks:", err);
  }
}

// Stakeholders Directory
async function loadStakeholders() {
  const tbody = document.getElementById("stakeholdersTableBody");
  if (!tbody) return;

  try {
    const res = await fetch(`${API_BASE}/api/stakeholders`);
    if (!res.ok) return;
    const stakeholders = await res.json();

    if (stakeholders.length === 0) {
      tbody.innerHTML = `<tr><td colspan="4" style="text-align:center; padding:2rem; color:var(--text-muted);">No stakeholders added.</td></tr>`;
      return;
    }

    const isAdmin = currentUser?.role === "admin";

    tbody.innerHTML = stakeholders.map(s => `
      <tr>
        <td style="font-weight: 600;">${escapeHtml(s.name)}</td>
        <td style="color: var(--text-muted);">${escapeHtml(s.role)}</td>
        <td>
          <a href="mailto:${escapeHtml(s.contact)}" style="color:var(--primary); text-decoration:none;">
            ${escapeHtml(s.contact)}
          </a>
        </td>
        <td style="text-align: right;">
          ${isAdmin ? `
            <button class="btn btn-secondary btn-sm delete-stakeholder-btn" data-id="${s.id}" title="Delete stakeholder" style="color:var(--neg); padding:2px 6px;">
              <i data-lucide="trash-2" style="width:12px; height:12px;"></i>
            </button>
          ` : '<span style="font-size:0.75rem; color:var(--text-light);">-</span>'}
        </td>
      </tr>
    `).join("");

    if (window.lucide) lucide.createIcons();

    tbody.querySelectorAll(".delete-stakeholder-btn").forEach(btn => {
      btn.addEventListener("click", async () => {
        if (!confirm("Delete this stakeholder?")) return;
        const id = btn.dataset.id;
        try {
          const res = await fetch(`${API_BASE}/api/stakeholders/${id}`, {
            method: "DELETE",
            headers: getAuthHeaders(false)
          });
          if (!res.ok) throw new Error("Failed to delete stakeholder");
          loadStakeholders();
          loadProjectData();
        } catch (err) {
          alert(err.message);
        }
      });
    });
  } catch (err) {
    console.error("Failed to load stakeholders:", err);
  }
}

// ==============================================================================
// 7. Enterprise System: Distinct Issues & Master-Detail Focus (Subject 3)
// ==============================================================================

async function loadCategories() {
  try {
    const res = await fetch(`${API_BASE}/api/categories`);
    if (!res.ok) return;
    const categories = await res.json();
    cachedCategories = categories;

    const filterSelect = document.getElementById("filterIssueCategory");
    const modalSelect = document.getElementById("issueCategory");

    if (filterSelect) {
      filterSelect.innerHTML = `<option value="">All Departments</option>` +
        categories.map(c => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join("");
    }

    if (modalSelect) {
      modalSelect.innerHTML = categories.map(c => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join("");
    }
  } catch (err) {
    console.error("Failed to load categories:", err);
  }
}

async function loadIssueStats() {
  try {
    const url = selectedAnalysisId
      ? `${API_BASE}/api/issues/stats?analysis_id=${selectedAnalysisId}`
      : `${API_BASE}/api/issues/stats`;

    const res = await fetch(url);
    if (!res.ok) return;
    const stats = await res.json();

    const totalEl = document.getElementById("kpiTotalIssues");
    const newEl = document.getElementById("kpiNewIssues");
    const inProgEl = document.getElementById("kpiInProgressIssues");
    const resolvedEl = document.getElementById("kpiResolvedIssues");

    if (totalEl) totalEl.textContent = stats.total || 0;
    if (newEl) newEl.textContent = stats.new || 0;
    if (inProgEl) inProgEl.textContent = stats.in_progress || 0;
    if (resolvedEl) resolvedEl.textContent = stats.resolved || 0;

    const sbIssues = document.getElementById("sidebarOpenIssues");
    if (sbIssues) sbIssues.textContent = (stats.new || 0) + (stats.in_progress || 0);

    // Header nav badge count for open issues
    if (navIssuesBadge) {
      const openCount = (stats.new || 0) + (stats.in_progress || 0);
      if (openCount > 0) {
        navIssuesBadge.style.display = "inline-flex";
        navIssuesBadge.textContent = openCount;
      } else {
        navIssuesBadge.style.display = "none";
      }
    }
  } catch (err) {
    console.error("Failed to load issue stats:", err);
  }
}

async function loadIssues() {
  const listContainer = document.getElementById("issuesSelectableList");
  const detailContainer = document.getElementById("selectedIssueContainer");
  if (!listContainer || !detailContainer) return;

  const statusFilter = document.getElementById("filterIssueStatus")?.value || "";
  const priorityFilter = document.getElementById("filterIssuePriority")?.value || "";
  const categoryFilter = document.getElementById("filterIssueCategory")?.value || "";

  const params = new URLSearchParams();
  if (selectedAnalysisId) params.append("analysis_id", selectedAnalysisId);
  if (statusFilter) params.append("status", statusFilter);
  if (priorityFilter) params.append("priority", priorityFilter);
  if (categoryFilter) params.append("category", categoryFilter);

  // Update scope badge with active event name
  const activeAnalysisObj = allAnalyses.find(a => a.id === selectedAnalysisId);
  const scopeBadge = document.getElementById("issuesScopeBadge");
  if (scopeBadge) {
    scopeBadge.textContent = activeAnalysisObj ? activeAnalysisObj.event_name : "Selected Event";
  }

  try {
    const res = await fetch(`${API_BASE}/api/issues?${params.toString()}`);
    if (!res.ok) throw new Error("Could not fetch issues");
    const issues = await res.json();
    cachedIssuesList = issues;

    const countBadge = document.getElementById("issuesCountBadge");
    if (countBadge) countBadge.textContent = issues.length;

    if (issues.length === 0) {
      listContainer.innerHTML = `
        <div style="text-align: center; padding: 2.5rem 1rem; color: var(--text-muted); font-size: 0.8rem;">
          <i data-lucide="inbox" style="width: 28px; height: 28px; stroke-width: 1.5; opacity: 0.5; margin-bottom: 0.4rem; display: inline-block;"></i>
          <div style="font-weight: 600; color: var(--text-main); margin-bottom: 0.2rem;">No Distinct Issues Found</div>
          <div>No negative sentiment tickets match this filter.</div>
        </div>`;

      detailContainer.innerHTML = `
        <div style="text-align: center; padding: 3.5rem 1.5rem; color: var(--text-muted);">
          <i data-lucide="check-circle" style="width: 44px; height: 44px; color: var(--pos); margin-bottom: 0.85rem; stroke-width: 1.5; display: inline-block;"></i>
          <h4 style="font-size: 1.1rem; font-weight: 700; color: var(--text-main); margin-bottom: 0.4rem;">
            No Issues for ${escapeHtml(activeAnalysisObj?.event_name || "this event")}
          </h4>
          <p style="font-size: 0.85rem; max-width: 420px; margin: 0 auto 1.5rem; line-height: 1.5;">
            No negative sentiment student remarks have been converted into operational tickets for this event.
          </p>
          ${currentUser?.role === 'admin' && selectedAnalysisId ? `
            <button class="btn btn-primary btn-sm" id="emptyStateGenerateIssuesBtn">
              <i data-lucide="zap"></i>
              <span>Generate Issues for this Event</span>
            </button>
          ` : ''}
        </div>`;

      document.getElementById("emptyStateGenerateIssuesBtn")?.addEventListener("click", () => {
        triggerCreateIssuesFromSelectedScope(selectedAnalysisId);
      });

      if (window.lucide) lucide.createIcons();
      return;
    }

    // Determine which issue to focus on: keep existing selection if in list, otherwise select the first one
    const issueExists = issues.some(i => i.id === selectedIssueId);
    if (!issueExists) {
      selectedIssueId = issues[0].id;
    }

    // 1. Render Left Panel: Distinct Selectable Issues List
    listContainer.innerHTML = issues.map(iss => {
      const isSelected = iss.id === selectedIssueId;
      const priorityClass = iss.priority.toLowerCase();
      const statusPillClass = iss.status === 'resolved' ? 'low' : (iss.status === 'in-progress' ? 'medium' : 'open');
      const statusLabel = iss.status === 'in-progress' ? 'In Prog' : (iss.status === 'new' ? 'New' : 'Resolved');

      return `
        <div class="issue-select-item ${isSelected ? 'selected' : ''}" data-id="${iss.id}">
          <div class="issue-select-item-top">
            <div style="display:flex; align-items:center; gap:0.4rem;">
              <span style="font-weight:700; font-size:0.78rem; color:var(--text-main);">#${iss.id}</span>
              <span class="badge-pill ${priorityClass}">${iss.priority}</span>
            </div>
            <span class="badge-pill ${statusPillClass}" style="font-size:0.65rem;">${statusLabel}</span>
          </div>
          <div class="issue-select-snippet">
            "${escapeHtml(iss.source_feedback_text)}"
          </div>
          <div style="display:flex; align-items:center; justify-content:space-between; margin-top:0.35rem; font-size:0.7rem; color:var(--text-light);">
            <span>${escapeHtml(iss.category)}</span>
          </div>
        </div>
      `;
    }).join("");

    // 2. Render Right Panel: SHOW ONLY THE SELECTED ONE!
    const selectedIssue = issues.find(i => i.id === selectedIssueId) || issues[0];
    renderSelectedIssueDetail(selectedIssue);

    // Attach click listeners to list items for single-issue focus
    listContainer.querySelectorAll(".issue-select-item").forEach(itemEl => {
      itemEl.addEventListener("click", () => {
        const clickedId = parseInt(itemEl.dataset.id);
        if (selectedIssueId !== clickedId) {
          selectedIssueId = clickedId;
          // Update selected style in list
          listContainer.querySelectorAll(".issue-select-item").forEach(el => el.classList.remove("selected"));
          itemEl.classList.add("selected");
          // Re-render detail view for ONLY this selected issue
          const iss = cachedIssuesList.find(i => i.id === clickedId);
          if (iss) renderSelectedIssueDetail(iss);
        }
      });
    });

    if (window.lucide) lucide.createIcons();
  } catch (err) {
    listContainer.innerHTML = `
      <div style="text-align: center; padding: 1.5rem; color: var(--neg); font-size: 0.825rem;">
        Failed to load issues for this event.
      </div>`;
    detailContainer.innerHTML = ``;
  }
}

// Render Focused View for ONLY the Selected Issue
function renderSelectedIssueDetail(issue) {
  const container = document.getElementById("selectedIssueContainer");
  if (!container || !issue) return;

  const isAdmin = currentUser?.role === "admin";
  const priorityClass = issue.priority.toLowerCase();
  const statusPillClass = issue.status === 'resolved' ? 'low' : (issue.status === 'in-progress' ? 'medium' : 'open');
  const statusLabel = issue.status === 'in-progress' ? 'In Progress' : (issue.status === 'new' ? 'New' : 'Resolved');

  container.innerHTML = `
    <div class="selected-issue-header">
      <div>
        <div class="selected-issue-title">
          <span>Issue Ticket #${issue.id}</span>
          <span class="badge-pill ${priorityClass}">${issue.priority}</span>
          <span class="badge-pill ${statusPillClass}">${statusLabel}</span>
        </div>
        <div style="font-size:0.78rem; color:var(--text-muted); margin-top:0.35rem; display:flex; align-items:center; gap:0.75rem; flex-wrap:wrap;">
          <span>Origin Event: <strong>${escapeHtml(issue.event_name)}</strong></span>
          <span>&bull;</span>
          <span>Filed: ${escapeHtml(issue.created_at)}</span>
        </div>
      </div>
      ${isAdmin ? `
        <button id="deleteSelectedIssueBtn" class="btn btn-secondary btn-sm" title="Delete this issue" style="color:var(--neg);">
          <i data-lucide="trash-2" style="width:13px; height:13px;"></i>
          <span>Delete</span>
        </button>
      ` : ''}
    </div>

    <div class="selected-issue-quote">
      "${escapeHtml(issue.source_feedback_text)}"
    </div>

    <div class="selected-issue-meta-grid">
      <div>
        <div class="meta-field-label">Assigned Department</div>
        <div class="meta-field-value" id="detailCategoryLabel">${escapeHtml(issue.category)}</div>
      </div>
      <div>
        <div class="meta-field-label">Severity Level</div>
        <div class="meta-field-value" id="detailPriorityLabel">${escapeHtml(issue.priority)} Priority</div>
      </div>
      <div>
        <div class="meta-field-label">Workflow Lifecycle</div>
        <div class="meta-field-value" id="detailStatusLabel" style="text-transform: capitalize;">${escapeHtml(issue.status)}</div>
      </div>
    </div>

    <div class="selected-issue-actions-bar">
      <div class="workflow-status-group">
        <span style="font-size:0.78rem; font-weight:600; color:var(--text-muted); margin-right:0.25rem;">Lifecycle Action:</span>
        <button class="workflow-btn ${issue.status === 'new' ? 'active new' : ''}" data-status="new" ${!isAdmin ? 'disabled' : ''} title="${isAdmin ? 'Set to New' : 'Admin required'}">
          <i data-lucide="alert-circle" style="width:12px; height:12px;"></i>
          <span>New</span>
        </button>
        <button class="workflow-btn ${issue.status === 'in-progress' ? 'active in-progress' : ''}" data-status="in-progress" ${!isAdmin ? 'disabled' : ''} title="${isAdmin ? 'Set to In Progress' : 'Admin required'}">
          <i data-lucide="clock" style="width:12px; height:12px;"></i>
          <span>In Progress</span>
        </button>
        <button class="workflow-btn ${issue.status === 'resolved' ? 'active resolved' : ''}" data-status="resolved" ${!isAdmin ? 'disabled' : ''} title="${isAdmin ? 'Mark Resolved' : 'Admin required'}">
          <i data-lucide="check-circle" style="width:12px; height:12px;"></i>
          <span>Resolved</span>
        </button>
      </div>

      ${isAdmin ? `
        <div style="display:flex; align-items:center; gap:0.5rem;">
          <label for="detailCategorySelect" style="font-size:0.75rem; color:var(--text-muted); font-weight:600;">Dept:</label>
          <select id="detailCategorySelect" class="form-select" style="font-size:0.76rem; padding:3px 6px;">
            ${cachedCategories.map(c => `
              <option value="${escapeHtml(c)}" ${c === issue.category ? 'selected' : ''}>${escapeHtml(c)}</option>
            `).join("")}
          </select>
        </div>
      ` : ''}
    </div>
  `;

  if (window.lucide) lucide.createIcons();

  if (isAdmin) {
    // Quick Category Changer
    const catSelect = document.getElementById("detailCategorySelect");
    if (catSelect) {
      catSelect.addEventListener("change", async (e) => {
        const newCat = e.target.value;
        try {
          const res = await fetch(`${API_BASE}/api/issues/${issue.id}`, {
            method: "PATCH",
            headers: getAuthHeaders(true),
            body: JSON.stringify({ category: newCat })
          });
          if (!res.ok) throw new Error("Failed to update department category");
          issue.category = newCat;
          document.getElementById("detailCategoryLabel").textContent = newCat;
          loadIssues(); // refresh list snippet
        } catch (err) {
          alert(err.message);
        }
      });
    }

    // Workflow Status Transition Buttons
    container.querySelectorAll(".workflow-btn").forEach(btn => {
      btn.addEventListener("click", async () => {
        const newStatus = btn.dataset.status;
        if (issue.status === newStatus) return;
        try {
          const res = await fetch(`${API_BASE}/api/issues/${issue.id}`, {
            method: "PATCH",
            headers: getAuthHeaders(true),
            body: JSON.stringify({ status: newStatus })
          });
          if (!res.ok) throw new Error("Failed to update issue status");
          issue.status = newStatus;
          loadIssueStats();
          renderSelectedIssueDetail(issue);

          // Update corresponding item in left list
          const listBadge = document.querySelector(`.issue-select-item[data-id="${issue.id}"] .badge-pill:last-child`);
          if (listBadge) {
            listBadge.className = `badge-pill ${newStatus === 'resolved' ? 'low' : (newStatus === 'in-progress' ? 'medium' : 'open')}`;
            listBadge.textContent = newStatus === 'in-progress' ? 'In Prog' : (newStatus === 'new' ? 'New' : 'Resolved');
          }
        } catch (err) {
          alert(err.message);
        }
      });
    });

    // Delete Button
    document.getElementById("deleteSelectedIssueBtn")?.addEventListener("click", async () => {
      if (!confirm(`Delete issue ticket #${issue.id}?`)) return;
      try {
        const res = await fetch(`${API_BASE}/api/issues/${issue.id}`, {
          method: "DELETE",
          headers: getAuthHeaders(false)
        });
        if (!res.ok) throw new Error("Failed to delete issue");
        selectedIssueId = null;
        loadIssues();
        loadIssueStats();
      } catch (err) {
        alert(err.message);
      }
    });
  }
}

async function triggerCreateIssuesFromSelectedScope(analysisId) {
  if (!analysisId) return;
  if (!currentUser) {
    openModal("loginModal");
    return;
  }
  if (currentUser.role !== "admin") {
    alert("Admin role required to generate issues.");
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/api/analyses/${analysisId}/create-issues?threshold=-0.30`, {
      method: "POST",
      headers: getAuthHeaders(false),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to generate issues.");
    }
    const result = await res.json();
    alert(`Generated ${result.created_count} distinct issues for this event (${result.skipped_duplicates} duplicate items skipped).`);
    selectedIssueId = null;
    loadIssues();
    loadIssueStats();
  } catch (err) {
    alert(err.message);
  }
}

// ==============================================================================
// 8. Modals & Form Submission Handlers
// ==============================================================================

function setupModalHandlers() {
  // Open buttons
  document.getElementById("editProjectBtn")?.addEventListener("click", () => openModal("editProjectModal"));
  document.getElementById("openAddTaskModalBtn")?.addEventListener("click", () => openModal("taskModal"));
  document.getElementById("openAddMilestoneModalBtn")?.addEventListener("click", () => openModal("milestoneModal"));
  document.getElementById("openAddRiskModalBtn")?.addEventListener("click", () => openModal("riskModal"));
  document.getElementById("openAddStakeholderModalBtn")?.addEventListener("click", () => openModal("stakeholderModal"));
  document.getElementById("openAddIssueModalBtn")?.addEventListener("click", () => openModal("issueModal"));

  // Close buttons with [data-close]
  document.querySelectorAll("[data-close]").forEach(btn => {
    btn.addEventListener("click", () => {
      const modalId = btn.dataset.close;
      closeModal(modalId);
    });
  });

  // Close on outside click
  document.querySelectorAll(".modal-overlay").forEach(overlay => {
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) {
        overlay.classList.add("hidden");
      }
    });
  });

  // Close on Escape key
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      document.querySelectorAll(".modal-overlay").forEach(m => m.classList.add("hidden"));
    }
  });

  // Demo Credentials quick fill buttons
  document.getElementById("demoAdminBtn")?.addEventListener("click", () => {
    document.getElementById("loginUsername").value = "admin";
    document.getElementById("loginPassword").value = "Admin@Event123";
    handleLogin("admin", "Admin@Event123");
  });

  document.getElementById("demoViewerBtn")?.addEventListener("click", () => {
    document.getElementById("loginUsername").value = "viewer";
    document.getElementById("loginPassword").value = "Viewer@Event123";
    handleLogin("viewer", "Viewer@Event123");
  });
}

function openModal(id) {
  const modal = document.getElementById(id);
  if (modal) {
    modal.classList.remove("hidden");
    const firstInput = modal.querySelector("input:not([type=hidden]), textarea, select");
    if (firstInput) setTimeout(() => firstInput.focus(), 50);
  }
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.add("hidden");
}

function setupFormSubmissions() {
  // Login Form
  document.getElementById("loginForm")?.addEventListener("submit", (e) => {
    e.preventDefault();
    const u = document.getElementById("loginUsername").value.trim();
    const p = document.getElementById("loginPassword").value;
    if (u && p) handleLogin(u, p);
  });

  // Edit Project Form
  document.getElementById("editProjectForm")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const payload = {
      name: document.getElementById("projEditName").value.trim(),
      start_date: document.getElementById("projEditStartDate").value,
      end_date: document.getElementById("projEditEndDate").value,
      status: document.getElementById("projEditStatus").value,
      description: document.getElementById("projEditDesc").value.trim(),
    };
    try {
      const res = await fetch(`${API_BASE}/api/project`, {
        method: "PUT",
        headers: getAuthHeaders(true),
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error("Failed to update project");
      closeModal("editProjectModal");
      loadProjectData();
    } catch (err) {
      alert(err.message);
    }
  });

  // Add Task Form
  document.getElementById("taskForm")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const payload = {
      title: document.getElementById("taskTitle").value.trim(),
      status: document.getElementById("taskStatus").value,
      due_date: document.getElementById("taskDueDate").value || null,
      assigned_to: document.getElementById("taskAssignedTo").value.trim() || null,
    };
    try {
      const res = await fetch(`${API_BASE}/api/tasks`, {
        method: "POST",
        headers: getAuthHeaders(true),
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error("Failed to create task");
      document.getElementById("taskForm").reset();
      closeModal("taskModal");
      loadTasks();
      loadProjectData();
    } catch (err) {
      alert(err.message);
    }
  });

  // Add Milestone Form
  document.getElementById("milestoneForm")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const payload = {
      title: document.getElementById("milestoneTitle").value.trim(),
      target_date: document.getElementById("milestoneTargetDate").value,
      completed: false,
    };
    try {
      const res = await fetch(`${API_BASE}/api/milestones`, {
        method: "POST",
        headers: getAuthHeaders(true),
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error("Failed to create milestone");
      document.getElementById("milestoneForm").reset();
      closeModal("milestoneModal");
      loadMilestones();
      loadProjectData();
    } catch (err) {
      alert(err.message);
    }
  });

  // Add Risk Form
  document.getElementById("riskForm")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const payload = {
      description: document.getElementById("riskDescription").value.trim(),
      likelihood: document.getElementById("riskLikelihood").value,
      impact: document.getElementById("riskImpact").value,
      mitigation: document.getElementById("riskMitigation").value.trim(),
      status: document.getElementById("riskStatus").value,
    };
    try {
      const res = await fetch(`${API_BASE}/api/risks`, {
        method: "POST",
        headers: getAuthHeaders(true),
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error("Failed to create risk");
      document.getElementById("riskForm").reset();
      closeModal("riskModal");
      loadRisks();
      loadProjectData();
    } catch (err) {
      alert(err.message);
    }
  });

  // Add Stakeholder Form
  document.getElementById("stakeholderForm")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const payload = {
      name: document.getElementById("stakeholderName").value.trim(),
      role: document.getElementById("stakeholderRole").value.trim(),
      contact: document.getElementById("stakeholderContact").value.trim(),
    };
    try {
      const res = await fetch(`${API_BASE}/api/stakeholders`, {
        method: "POST",
        headers: getAuthHeaders(true),
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error("Failed to create stakeholder");
      document.getElementById("stakeholderForm").reset();
      closeModal("stakeholderModal");
      loadStakeholders();
      loadProjectData();
    } catch (err) {
      alert(err.message);
    }
  });

  // Manual Issue Form
  document.getElementById("issueForm")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const payload = {
      analysis_id: selectedAnalysisId || currentAnalysisId || null,
      source_feedback_text: document.getElementById("issueFeedbackText").value.trim(),
      category: document.getElementById("issueCategory").value,
      priority: document.getElementById("issuePriority").value,
      status: "new",
    };
    try {
      const res = await fetch(`${API_BASE}/api/issues`, {
        method: "POST",
        headers: getAuthHeaders(true),
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error("Failed to create issue");
      document.getElementById("issueForm").reset();
      closeModal("issueModal");
      loadIssues();
      loadIssueStats();
    } catch (err) {
      alert(err.message);
    }
  });
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// ==============================================================================
// 12. Database Architecture & Live Transaction Telemetry Module
// ==============================================================================

let dbOverviewData = null;
let activeDbTable = "analyses";
let dbCurrentPage = 1;
let dbPageSize = 25;
let dbTableSearch = "";
let dbTxFilterAction = "ALL";
let dbTxFilterTable = "ALL";
let dbTxSearch = "";
let isDbStreamPolling = true;
let dbPollTimer = null;
let dbDebounceTableSearch = null;
let dbDebounceTxSearch = null;

async function initDatabaseModule() {
  const tableSelect = document.getElementById("dbActiveTableSelect");
  const pageSizeSelect = document.getElementById("dbPageSizeSelect");
  const tableSearchInput = document.getElementById("dbTableSearchInput");
  const prevBtn = document.getElementById("dbPagePrevBtn");
  const nextBtn = document.getElementById("dbPageNextBtn");
  const refreshBtn = document.getElementById("dbRefreshAllBtn");
  const streamToggleBtn = document.getElementById("dbLiveStreamToggleBtn");
  const simulateBtn = document.getElementById("dbSimulateActionBtn");
  const clearTxBtn = document.getElementById("dbClearTxBtn");
  const txActionFilter = document.getElementById("dbTxActionFilter");
  const txTableFilter = document.getElementById("dbTxTableFilter");
  const txSearchInput = document.getElementById("dbTxSearchInput");

  // Table selection change
  if (tableSelect) {
    tableSelect.addEventListener("change", (e) => {
      activeDbTable = e.target.value;
      dbCurrentPage = 1;
      renderTableSchema();
      loadTableData();
    });
  }

  // Page size change
  if (pageSizeSelect) {
    pageSizeSelect.addEventListener("change", (e) => {
      dbPageSize = parseInt(e.target.value) || 25;
      dbCurrentPage = 1;
      loadTableData();
    });
  }

  // Table search with debounce
  if (tableSearchInput) {
    tableSearchInput.addEventListener("input", (e) => {
      clearTimeout(dbDebounceTableSearch);
      dbDebounceTableSearch = setTimeout(() => {
        dbTableSearch = e.target.value.trim();
        dbCurrentPage = 1;
        loadTableData();
      }, 300);
    });
  }

  // Pagination buttons
  if (prevBtn) {
    prevBtn.addEventListener("click", () => {
      if (dbCurrentPage > 1) {
        dbCurrentPage--;
        loadTableData();
      }
    });
  }

  if (nextBtn) {
    nextBtn.addEventListener("click", () => {
      dbCurrentPage++;
      loadTableData();
    });
  }

  // Refresh all button
  if (refreshBtn) {
    refreshBtn.addEventListener("click", async () => {
      refreshBtn.querySelector("i")?.classList.add("spin");
      await loadDatabaseOverview();
      await loadTableData();
      await loadTransactionStream();
      setTimeout(() => refreshBtn.querySelector("i")?.classList.remove("spin"), 600);
    });
  }

  // Stream toggle button
  if (streamToggleBtn) {
    streamToggleBtn.addEventListener("click", () => {
      isDbStreamPolling = !isDbStreamPolling;
      const dot = document.getElementById("dbStreamDot");
      const txt = document.getElementById("dbLiveStreamStatusText");
      if (isDbStreamPolling) {
        dot?.classList.add("active");
        if (txt) txt.textContent = "Stream: ON";
        startDbStreamPolling();
      } else {
        dot?.classList.remove("active");
        if (txt) txt.textContent = "Stream: PAUSED";
        stopDbStreamPolling();
      }
    });
  }

  // Main simulate button
  if (simulateBtn) {
    simulateBtn.addEventListener("click", () => {
      simulateDatabaseAction();
    });
  }

  // Quick simulation buttons
  document.querySelectorAll(".db-quick-sim-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const act = btn.getAttribute("data-action");
      simulateDatabaseAction(act);
    });
  });

  // Clear audit logs button
  if (clearTxBtn) {
    clearTxBtn.addEventListener("click", clearDatabaseLogs);
  }

  // Transaction filter listeners
  if (txActionFilter) {
    txActionFilter.addEventListener("change", (e) => {
      dbTxFilterAction = e.target.value;
      loadTransactionStream();
    });
  }

  if (txTableFilter) {
    txTableFilter.addEventListener("change", (e) => {
      dbTxFilterTable = e.target.value;
      loadTransactionStream();
    });
  }

  if (txSearchInput) {
    txSearchInput.addEventListener("input", (e) => {
      clearTimeout(dbDebounceTxSearch);
      dbDebounceTxSearch = setTimeout(() => {
        dbTxSearch = e.target.value.trim();
        loadTransactionStream();
      }, 300);
    });
  }

  // Initial load
  await loadDatabaseOverview();
  await loadTableData();
  await loadTransactionStream();
  startDbStreamPolling();
}

async function loadDatabaseOverview() {
  try {
    const res = await fetch(`${API_BASE}/api/database/overview`);
    if (!res.ok) throw new Error("Database introspection failed");
    dbOverviewData = await res.json();

    // Update KPI metrics
    const kpiSize = document.getElementById("dbKpiSize");
    const kpiPages = document.getElementById("dbKpiPages");
    const kpiTables = document.getElementById("dbKpiTables");
    const kpiEngine = document.getElementById("dbKpiEngine");
    const kpiRows = document.getElementById("dbKpiRows");
    const kpiTxTotal = document.getElementById("dbKpiTxTotal");

    if (kpiSize) kpiSize.textContent = dbOverviewData.file_size_formatted || "0 KB";
    if (kpiPages) kpiPages.textContent = `${dbOverviewData.page_count?.toLocaleString() || 0} pages • ${dbOverviewData.page_size || 4096}B`;
    if (kpiTables) kpiTables.textContent = dbOverviewData.total_tables || 0;
    if (kpiEngine) kpiEngine.textContent = `SQLite ${dbOverviewData.sqlite_version || "3.x"} • ${dbOverviewData.journal_mode || "WAL"} Mode`;
    if (kpiRows) kpiRows.textContent = (dbOverviewData.total_rows || 0).toLocaleString();
    if (kpiTxTotal) kpiTxTotal.textContent = (dbOverviewData.total_transactions || 0).toLocaleString();

    // Populate active table dropdown if options exist
    const tableSelect = document.getElementById("dbActiveTableSelect");
    if (tableSelect && dbOverviewData.tables) {
      const currentVal = tableSelect.value || activeDbTable;
      tableSelect.innerHTML = dbOverviewData.tables.map(t => `
        <option value="${escapeHtml(t.name)}" ${t.name === currentVal ? "selected" : ""}>
          ${escapeHtml(t.name)} (${t.row_count.toLocaleString()})
        </option>
      `).join("");
      activeDbTable = tableSelect.value;
    }

    // Populate table filter dropdown in transaction stream
    const txTableFilter = document.getElementById("dbTxTableFilter");
    if (txTableFilter && dbOverviewData.tables) {
      const currentVal = txTableFilter.value || "ALL";
      txTableFilter.innerHTML = `<option value="ALL">All Tables</option>` + dbOverviewData.tables.map(t => `
        <option value="${escapeHtml(t.name)}" ${t.name === currentVal ? "selected" : ""}>
          ${escapeHtml(t.name)}
        </option>
      `).join("");
    }

    renderTableSchema();
  } catch (err) {
    console.error("Failed to load database overview:", err);
  }
}

function renderTableSchema() {
  const container = document.getElementById("dbSchemaChips");
  if (!container || !dbOverviewData || !dbOverviewData.tables) return;

  const tableObj = dbOverviewData.tables.find(t => t.name === activeDbTable);
  if (!tableObj || !tableObj.columns) {
    container.innerHTML = `<span style="color:var(--text-muted); font-size:0.75rem;">No schema available</span>`;
    return;
  }

  container.innerHTML = tableObj.columns.map(col => `
    <div class="schema-chip ${col.pk ? 'is-pk' : ''}" title="${col.pk ? 'Primary Key' : ''} ${col.notnull ? '• NOT NULL' : ''}">
      ${col.pk ? '<span class="schema-pk-tag">PK</span>' : ''}
      <span class="schema-chip-name">${escapeHtml(col.name)}</span>
      <span class="schema-type-tag">${escapeHtml(col.type)}</span>
    </div>
  `).join("");
}

async function loadTableData() {
  const thead = document.getElementById("dbDataTableHead");
  const tbody = document.getElementById("dbDataTableBody");
  const paginationInfo = document.getElementById("dbTablePaginationInfo");
  const pageCounter = document.getElementById("dbPageCurrentText");
  const prevBtn = document.getElementById("dbPagePrevBtn");
  const nextBtn = document.getElementById("dbPageNextBtn");

  if (!tbody) return;

  try {
    const params = new URLSearchParams({
      page: dbCurrentPage,
      page_size: dbPageSize,
    });
    if (dbTableSearch) params.append("search", dbTableSearch);

    const res = await fetch(`${API_BASE}/api/database/tables/${encodeURIComponent(activeDbTable)}?${params.toString()}`);
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || "Failed to load table records");
    }

    const data = await res.json();
    const columns = data.columns || [];
    const rows = data.rows || [];
    const totalRows = data.total_rows || 0;
    const totalPages = data.total_pages || 1;

    // Update pagination controls
    if (paginationInfo) {
      if (totalRows === 0) {
        paginationInfo.textContent = "Showing 0 rows";
      } else {
        const start = (dbCurrentPage - 1) * dbPageSize + 1;
        const end = Math.min(dbCurrentPage * dbPageSize, totalRows);
        paginationInfo.textContent = `Showing ${start} - ${end} of ${totalRows.toLocaleString()} rows`;
      }
    }

    if (pageCounter) {
      pageCounter.textContent = `${dbCurrentPage} / ${totalPages}`;
    }

    if (prevBtn) prevBtn.disabled = dbCurrentPage <= 1;
    if (nextBtn) nextBtn.disabled = dbCurrentPage >= totalPages;

    // Render Table Header
    if (thead) {
      thead.innerHTML = `
        <tr>
          ${columns.map(c => `
            <th title="${c.pk ? 'Primary Key' : ''}">
              ${escapeHtml(c.name)} ${c.pk ? '<span style="color:var(--primary); font-size:0.6rem;">[PK]</span>' : ''}
            </th>
          `).join("")}
          <th style="text-align: right;">Inspect</th>
        </tr>
      `;
    }

    // Render Table Body
    if (rows.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="${columns.length + 1}" style="text-align: center; padding: 3rem 1rem; color: var(--text-muted);">
            <div style="font-weight: 600; margin-bottom: 0.25rem;">No records found</div>
            <div style="font-size: 0.75rem;">${dbTableSearch ? `No rows matching "${escapeHtml(dbTableSearch)}"` : "This table contains zero records."}</div>
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = rows.map((row, idx) => {
      return `
        <tr>
          ${columns.map(c => {
            const val = row[c.name];
            let cellHtml = "";

            if (val === null || val === undefined) {
              cellHtml = `<span class="db-null-val">null</span>`;
            } else if (c.pk) {
              cellHtml = `<span class="db-pk-val">#${escapeHtml(val)}</span>`;
            } else if (typeof val === "string" && (val.startsWith("{") || val.startsWith("["))) {
              try {
                JSON.parse(val);
                cellHtml = `<button class="db-json-chip view-row-json-btn" data-row-idx="${idx}" data-col="${escapeHtml(c.name)}" title="Inspect JSON payload">JSON Object</button>`;
              } catch {
                cellHtml = escapeHtml(val);
              }
            } else if (typeof val === "number") {
              cellHtml = `<span class="db-cell-mono">${val}</span>`;
            } else {
              cellHtml = escapeHtml(String(val));
            }

            return `<td title="${escapeHtml(String(val ?? ''))}">${cellHtml}</td>`;
          }).join("")}
          <td style="text-align: right;">
            <button class="btn btn-secondary btn-sm inspect-full-row-btn" data-row-idx="${idx}" title="Inspect full record" style="padding: 2px 7px; font-size: 0.7rem;">
              <i data-lucide="eye" style="width: 12px; height: 12px;"></i>
            </button>
          </td>
        </tr>
      `;
    }).join("");

    if (window.lucide) lucide.createIcons();

    // Attach row inspection handlers
    tbody.querySelectorAll(".inspect-full-row-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const idx = parseInt(btn.dataset.rowIdx);
        const rowData = rows[idx];
        if (rowData) {
          openDbRowDetailModal(`${activeDbTable} Record #${rowData.id || idx + 1}`, rowData);
        }
      });
    });

    tbody.querySelectorAll(".view-row-json-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const idx = parseInt(btn.dataset.rowIdx);
        const col = btn.dataset.col;
        const rowData = rows[idx];
        if (rowData && rowData[col]) {
          try {
            const parsed = JSON.parse(rowData[col]);
            openDbRowDetailModal(`${activeDbTable} • ${col}`, parsed);
          } catch {
            openDbRowDetailModal(`${activeDbTable} • ${col}`, rowData[col]);
          }
        }
      });
    });
  } catch (err) {
    console.error("Failed to load table data:", err);
    tbody.innerHTML = `
      <tr>
        <td colspan="10" style="text-align: center; padding: 2.5rem; color: var(--neg);">
          Error loading table records: ${escapeHtml(err.message)}
        </td>
      </tr>
    `;
  }
}

async function loadTransactionStream() {
  const container = document.getElementById("dbTxStreamList");
  if (!container) return;

  try {
    const params = new URLSearchParams({ limit: 40 });
    if (dbTxFilterAction && dbTxFilterAction !== "ALL") params.append("action", dbTxFilterAction);
    if (dbTxFilterTable && dbTxFilterTable !== "ALL") params.append("table_name", dbTxFilterTable);
    if (dbTxSearch) params.append("search", dbTxSearch);

    const res = await fetch(`${API_BASE}/api/database/transactions?${params.toString()}`);
    if (!res.ok) throw new Error("Failed to fetch transaction stream");
    const data = await res.json();
    const logs = data.logs || [];

    if (logs.length === 0) {
      container.innerHTML = `
        <div style="text-align: center; padding: 3rem 1rem; color: var(--text-muted); font-size: 0.82rem;">
          <i data-lucide="inbox" style="width: 28px; height: 28px; opacity: 0.5; margin-bottom: 0.4rem; display: inline-block;"></i>
          <div style="font-weight: 600; color: var(--text-main);">No Transactions Recorded</div>
          <div>No transaction logs match current filters.</div>
        </div>
      `;
      if (window.lucide) lucide.createIcons();
      return;
    }

    container.innerHTML = logs.map(log => {
      const actLower = (log.action || "insert").toLowerCase();
      let detailsParsed = null;
      if (log.details) {
        try {
          detailsParsed = typeof log.details === "string" ? JSON.parse(log.details) : log.details;
        } catch {
          detailsParsed = log.details;
        }
      }

      return `
        <div class="db-tx-entry action-${actLower}" data-id="${log.id}">
          <div class="db-tx-top">
            <div class="db-tx-tags">
              <span class="tx-action-badge ${actLower}">${escapeHtml(log.action)}</span>
              <span class="tx-table-badge">${escapeHtml(log.table_name)}</span>
              <span class="tx-status-badge"><i data-lucide="check" style="width: 11px; height: 11px;"></i> COMMITTED</span>
            </div>
            <div class="db-tx-meta">
              <span class="tx-duration-badge" title="Execution duration">${log.duration_ms || 0.5} ms</span>
              <span title="${escapeHtml(log.timestamp || '')}">${formatTxTimestamp(log.timestamp)}</span>
            </div>
          </div>
          <div class="db-tx-summary">${escapeHtml(log.summary)}</div>
          <div class="db-tx-bottom">
            <span>IP: ${escapeHtml(log.client_ip || '127.0.0.1')}</span>
            ${detailsParsed ? `
              <button class="db-tx-inspect-btn inspect-tx-details-btn" data-id="${log.id}">
                <i data-lucide="code" style="width: 11px; height: 11px;"></i>
                <span>View Details</span>
              </button>
            ` : ''}
          </div>
        </div>
      `;
    }).join("");

    if (window.lucide) lucide.createIcons();

    // Attach inspect listeners
    container.querySelectorAll(".inspect-tx-details-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const id = parseInt(btn.dataset.id);
        const targetLog = logs.find(l => l.id === id);
        if (targetLog) {
          let det = targetLog.details;
          try {
            if (typeof det === "string") det = JSON.parse(det);
          } catch {}
          openDbRowDetailModal(`Transaction #${targetLog.id} • ${targetLog.action} on ${targetLog.table_name}`, {
            id: targetLog.id,
            action: targetLog.action,
            table: targetLog.table_name,
            summary: targetLog.summary,
            status: targetLog.status,
            duration_ms: targetLog.duration_ms,
            client_ip: targetLog.client_ip,
            timestamp: targetLog.timestamp,
            details: det,
          });
        }
      });
    });
  } catch (err) {
    console.error("Failed to load transaction stream:", err);
  }
}

function formatTxTimestamp(ts) {
  if (!ts) return "";
  try {
    const d = new Date(ts);
    return isNaN(d.getTime()) ? ts : d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch {
    return ts;
  }
}

async function simulateDatabaseAction(actionType = null) {
  try {
    const url = `${API_BASE}/api/database/transactions/simulate${actionType ? `?action_type=${encodeURIComponent(actionType)}` : ''}`;
    const res = await fetch(url, { method: "POST" });
    if (!res.ok) throw new Error("Simulation failed");
    const result = await res.json();

    // Refresh telemetry immediately
    await loadTransactionStream();
    await loadDatabaseOverview();

    // If simulated action affects current table, refresh table rows
    if (result.table_name === activeDbTable) {
      await loadTableData();
    }
  } catch (err) {
    alert("Transaction simulation failed: " + err.message);
  }
}

async function clearDatabaseLogs() {
  if (!confirm("Are you sure you want to reset and clear database transaction audit logs?")) return;
  try {
    const res = await fetch(`${API_BASE}/api/database/transactions`, { method: "DELETE" });
    if (!res.ok) throw new Error("Failed to clear logs");
    await loadTransactionStream();
    await loadDatabaseOverview();
  } catch (err) {
    alert("Failed to reset logs: " + err.message);
  }
}

function startDbStreamPolling() {
  stopDbStreamPolling();
  dbPollTimer = setInterval(() => {
    if (isDbStreamPolling) {
      loadTransactionStream();
    }
  }, 3500);
}

function stopDbStreamPolling() {
  if (dbPollTimer) {
    clearInterval(dbPollTimer);
    dbPollTimer = null;
  }
}

function openDbRowDetailModal(title, dataObj) {
  const modalTitle = document.getElementById("dbRowModalTitle");
  const modalContent = document.getElementById("dbRowModalContent");
  const modalSub = document.getElementById("dbRowModalSub");

  if (modalTitle) modalTitle.textContent = title || "Record Inspection";
  if (modalSub) modalSub.textContent = `Inspected on ${new Date().toLocaleTimeString()} • SQLite Active Buffer`;
  if (modalContent) {
    modalContent.textContent = typeof dataObj === "string" ? dataObj : JSON.stringify(dataObj, null, 2);
  }

  openModal("dbRowDetailModal");
}
