/* ============================================================================
   nav.js — shared page behaviour for every docs/ page. No dependencies.
   Wires: .page-nav buttons (data-nav="up" | "down" | "theme"),
          .side-nav__link active-state highlighting while scrolling.
   Include before </body>:  <script src="../resources/nav.js"></script>
   ============================================================================ */
(function () {
  "use strict";

  var slides = Array.prototype.slice.call(document.querySelectorAll("main > section[id]"));
  var links = Array.prototype.slice.call(document.querySelectorAll(".side-nav__link"));

  function linkFor(id) {
    for (var i = 0; i < links.length; i++) {
      if (links[i].getAttribute("href") === "#" + id) return links[i];
    }
    return null;
  }

  /* ---- current slide = last one whose top has passed the upper third ---- */
  function currentIndex() {
    var idx = 0;
    for (var i = 0; i < slides.length; i++) {
      if (slides[i].getBoundingClientRect().top <= window.innerHeight * 0.35) idx = i;
    }
    return idx;
  }

  function goTo(i) {
    var clamped = Math.max(0, Math.min(slides.length - 1, i));
    if (slides[clamped]) slides[clamped].scrollIntoView({ behavior: "smooth", block: "start" });
  }

  var upBtn = document.querySelector('[data-nav="up"]');
  var downBtn = document.querySelector('[data-nav="down"]');
  if (upBtn) upBtn.addEventListener("click", function () { goTo(currentIndex() - 1); });
  if (downBtn) downBtn.addEventListener("click", function () { goTo(currentIndex() + 1); });

  /* ---- theme toggle ---- */
  var themeBtn = document.querySelector('[data-nav="theme"]');
  if (themeBtn) themeBtn.addEventListener("click", function () {
    var root = document.documentElement;
    root.dataset.theme = root.dataset.theme === "dark" ? "light" : "dark";
  });

  /* ---- side-nav active highlight ---- */
  if (slides.length && links.length && "IntersectionObserver" in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        links.forEach(function (l) { l.classList.remove("is-active"); });
        var link = linkFor(entry.target.id);
        if (link) link.classList.add("is-active");
      });
    }, { rootMargin: "-35% 0px -55% 0px" });
    slides.forEach(function (s) { io.observe(s); });
  }
})();
