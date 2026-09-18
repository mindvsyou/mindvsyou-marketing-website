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

// ---- NAV TEMPLATE ----
function renderNav(activePage) {
  const pages = [
    { label: "Home",      href: "index.html" },
    { label: "Students",  href: "students.html" },
    { label: "About",     href: "about.html" },
    { label: "Blog",      href: "blog.html" },
    { label: "FAQ",       href: "faq.html" },
    { label: "Practice Now ↗", href: CONFIG.appLink, cta: true },
  ];
  const links = pages.map(p =>
    `<li><a href="${p.href}" class="${p.cta ? 'nav-cta' : ''}">${p.label}</a></li>`
  ).join('');

  document.getElementById('navbar').innerHTML = `
    <div class="nav-inner">
      <a class="nav-logo" href="index.html">${CONFIG.productName.replace(/(\w+)$/, '<span>$1</span>')}</a>
      <ul class="nav-links" id="navLinks">${links}</ul>
      <button class="hamburger" id="hamburger" aria-label="Menu">
        <span></span><span></span><span></span>
      </button>
    </div>`;

  document.getElementById('hamburger').addEventListener('click', () => {
    document.getElementById('navLinks').classList.toggle('open');
  });
}

// ---- FOOTER TEMPLATE ----
function renderFooter() {
  document.getElementById('footer').innerHTML = `
    <div class="footer-inner">
      <div class="footer-brand">
        <a class="logo" href="index.html">${CONFIG.productName.replace(/(\w+)$/, '<span>$1</span>')}</a>
        <p>Practice CBSE Class 10 MCQs and case-based questions online — no app download needed.</p>
      </div>
      <div class="footer-col">
        <h4>Product</h4>
        <ul>
          <li><a href="students.html">For Students</a></li>
          <li><a href="${CONFIG.appLink}">Try Free</a></li>
          <li><a href="faq.html">FAQ</a></li>
        </ul>
      </div>
      <div class="footer-col">
        <h4>Company</h4>
        <ul>
          <li><a href="about.html">About Us</a></li>
          <li><a href="blog.html">Blog</a></li>
          <li><a href="press.html">Press</a></li>
          <li><a href="contact.html">Contact</a></li>
        </ul>
      </div>
      <div class="footer-col">
        <h4>Connect</h4>
        <ul>
          <li><a href="${CONFIG.LinkedinLink}">Linkedin</a></li>
          <li><a href="${CONFIG.instagramLink}">Instagram</a></li>
          <li><a href="mailto:${CONFIG.contactEmail}">Email Us</a></li>
        </ul>
      </div>
    </div>
    <div class="footer-bottom">
      <p>© ${CONFIG.year} ${CONFIG.productName}, a product of Sparqity Private Limited. All rights reserved. Made with ❤️ for CBSE students.</p>
    </div>`;
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
  if (document.getElementById('navbar'))  renderNav();
  if (document.getElementById('footer'))  renderFooter();
  if (document.querySelector('.faq-list')) initFAQ();
  if (document.getElementById('scrollNudge')) initScrollNudge();
});
