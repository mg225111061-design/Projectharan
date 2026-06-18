/* Mr. Jeffrey — shared site script: theme (light/dark) + tiny helpers. Loaded by every page. */
(function () {
  "use strict";
  // ---- theme: persisted in localStorage; first visit follows the OS preference ----
  var KEY = "mrj-theme";
  function current() {
    var saved = null;
    try { saved = localStorage.getItem(KEY); } catch (e) {}
    if (saved === "light" || saved === "dark") return saved;
    return (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) ? "dark" : "light";
  }
  function apply(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    var btns = document.querySelectorAll("[data-theme-toggle]");
    for (var i = 0; i < btns.length; i++) btns[i].textContent = theme === "dark" ? "☾" : "☀";
  }
  function toggle() {
    var next = (document.documentElement.getAttribute("data-theme") === "dark") ? "light" : "dark";
    try { localStorage.setItem(KEY, next); } catch (e) {}
    apply(next);
  }
  apply(current());                                  // apply ASAP (before paint where possible)
  document.addEventListener("DOMContentLoaded", function () {
    apply(document.documentElement.getAttribute("data-theme") || current());
    var btns = document.querySelectorAll("[data-theme-toggle]");
    for (var i = 0; i < btns.length; i++) btns[i].addEventListener("click", toggle);
  });
  window.MRJ = window.MRJ || {};
  window.MRJ.toggleTheme = toggle;
  window.MRJ.currentTheme = current;

  // ---- auth state helper (used by headers): GET /api/auth/me → {authenticated, nickname?} ----
  window.MRJ.whoami = async function () {
    try {
      var r = await fetch("/api/auth/me", { credentials: "same-origin" });
      if (!r.ok) return { authenticated: false };
      return await r.json();
    } catch (e) { return { authenticated: false }; }
  };
})();
