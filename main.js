/* ============================================================
   BOARDBUDDY — SHARED JAVASCRIPT
   ============================================================ */

// ---- CONFIG: EDIT THESE ----
const CONFIG = {
  productName:    "MindVsYou",          // ← Change your product name here
  tagline:        "CBSE Board Prep, Online",
  appLink:        "https://quiz.mindvsyou.io",  // ← Your web app
  contactEmail:   "hello@mindvsyou.io",
  contactPhone:   "+91 84489 70354",
  LinkedinLink:    "https://www.linkedin.com/company/mindvsyou-ai",
  instagramLink:  "https://instagram.com/mindvsyou",
  year:           new Date().getFullYear(),
};

// ---- NAV / FOOTER ----
// Markup is written directly into each page's HTML so crawlers that don't run
// JavaScript still see every internal link. Keep the nav/footer identical across pages.
function initNav() {
  const btn = document.getElementById('hamburger');
  if (!btn) return;
  btn.addEventListener('click', () => {
    document.getElementById('navLinks').classList.toggle('open');
  });
}

function initFooterYear() {
  const el = document.getElementById('footerYear');
  if (el) el.textContent = CONFIG.year;
}

// ---- FAQ ACCORDION ----
function initFAQ() {
  document.querySelectorAll('.faq-q').forEach(btn => {
    btn.addEventListener('click', () => {
      const ans = btn.nextElementSibling;
      const isOpen = btn.classList.contains('open');
      document.querySelectorAll('.faq-q').forEach(b => { b.classList.remove('open'); b.nextElementSibling.classList.remove('open'); });
      if (!isOpen) { btn.classList.add('open'); ans.classList.add('open'); }
    });
  });
}

// ---- SCROLL NUDGE ----
function initScrollNudge() {
  const nudge = document.getElementById('scrollNudge');
  const DISMISS_KEY = 'mvy_scroll_nudge_dismissed';
  if (sessionStorage.getItem(DISMISS_KEY)) { nudge.remove(); return; }

  function dismiss() {
    nudge.classList.remove('show');
    sessionStorage.setItem(DISMISS_KEY, '1');
  }
  document.getElementById('scrollNudgeClose').addEventListener('click', dismiss);
  nudge.querySelector('.btn').addEventListener('click', dismiss);

  function onScroll() {
    const scrolledPast = window.scrollY + window.innerHeight;
    if (scrolledPast > document.documentElement.scrollHeight * 0.4) {
      nudge.classList.add('show');
      window.removeEventListener('scroll', onScroll);
    }
  }
  window.addEventListener('scroll', onScroll, { passive: true });
}

// ---- INIT ----
document.addEventListener('DOMContentLoaded', () => {
  initNav();
  initFooterYear();
  if (document.querySelector('.faq-list')) initFAQ();
  if (document.getElementById('scrollNudge')) initScrollNudge();
});
