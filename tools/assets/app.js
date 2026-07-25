/* Spring Boot 학습 가이드 — 가벼운 인터랙션
   의존성 없음. 실패해도 문서 읽기에는 영향이 없도록 각 기능을 독립적으로 감싼다. */
(function () {
  "use strict";

  function each(sel, fn, root) {
    Array.prototype.forEach.call((root || document).querySelectorAll(sel), fn);
  }
  function guard(name, fn) {
    try { fn(); } catch (e) { console.warn("[guide] " + name + " 초기화 실패:", e); }
  }

  /* 1) 코드블록 복사 버튼 ------------------------------------------------- */
  guard("code-copy", function () {
    each(".code-block", function (block) {
      var code = block.querySelector("pre");
      if (!code) return;
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "code-copy";
      btn.textContent = "복사";
      btn.setAttribute("aria-label", "코드 복사");
      btn.addEventListener("click", function () {
        var text = code.innerText.replace(/\n$/, "");
        var done = function () {
          btn.textContent = "복사됨";
          btn.classList.add("is-done");
          setTimeout(function () {
            btn.textContent = "복사";
            btn.classList.remove("is-done");
          }, 1400);
        };
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text).then(done, function () { fallback(text, done); });
        } else {
          fallback(text, done);
        }
      });
      block.appendChild(btn);
    });

    function fallback(text, done) {
      var ta = document.createElement("textarea");
      ta.value = text;
      ta.setAttribute("readonly", "");
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand("copy"); done(); } catch (e) { /* noop */ }
      document.body.removeChild(ta);
    }
  });

  /* 2) 탭 ----------------------------------------------------------------- */
  guard("tabs", function () {
    each(".tabs", function (tabs, idx) {
      var panels = tabs.querySelectorAll(":scope > .tab-panel");
      if (!panels.length) return;
      var bar = document.createElement("div");
      bar.className = "tab-bar";
      bar.setAttribute("role", "tablist");

      Array.prototype.forEach.call(panels, function (panel, i) {
        var id = "tab-" + idx + "-" + i;
        var btn = document.createElement("button");
        btn.type = "button";
        btn.textContent = panel.getAttribute("data-title") || "탭 " + (i + 1);
        btn.setAttribute("role", "tab");
        btn.setAttribute("aria-selected", i === 0 ? "true" : "false");
        btn.setAttribute("aria-controls", id);
        panel.id = id;
        panel.setAttribute("role", "tabpanel");
        if (i === 0) panel.setAttribute("data-active", ""); else panel.removeAttribute("data-active");
        btn.addEventListener("click", function () {
          each(":scope > .tab-bar > button", function (b) { b.setAttribute("aria-selected", "false"); }, tabs);
          Array.prototype.forEach.call(panels, function (p) { p.removeAttribute("data-active"); });
          btn.setAttribute("aria-selected", "true");
          panel.setAttribute("data-active", "");
        });
        bar.appendChild(btn);
      });
      tabs.insertBefore(bar, tabs.firstChild);
    });
  });

  /* 3) 도식 단계 포커스 --------------------------------------------------- */
  guard("diagram-focus", function () {
    each(".dg[data-focusable]", function (fig) {
      var parts = fig.querySelectorAll(".dg-node, .dg-steps > li, .lyr");
      if (!parts.length) return;
      Array.prototype.forEach.call(parts, function (part) {
        part.setAttribute("tabindex", "0");
        var toggle = function () {
          var on = part.classList.contains("is-focus");
          Array.prototype.forEach.call(parts, function (p) { p.classList.remove("is-focus"); });
          if (on) { fig.classList.remove("has-focus"); return; }
          part.classList.add("is-focus");
          fig.classList.add("has-focus");
        };
        part.addEventListener("click", toggle);
        part.addEventListener("keydown", function (e) {
          if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(); }
        });
      });
    });
  });

  /* 4) 목차 스크롤스파이 -------------------------------------------------- */
  guard("toc-spy", function () {
    var links = document.querySelectorAll(".toc a[href^='#']");
    if (!links.length || !("IntersectionObserver" in window)) return;
    var map = {};
    Array.prototype.forEach.call(links, function (a) {
      var el = document.getElementById(decodeURIComponent(a.getAttribute("href").slice(1)));
      if (el) map[el.id] = a;
    });
    var visible = [];
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        var id = en.target.id;
        var i = visible.indexOf(id);
        if (en.isIntersecting) { if (i < 0) visible.push(id); }
        else if (i >= 0) { visible.splice(i, 1); }
      });
      if (!visible.length) return;
      var order = Object.keys(map);
      var top = visible.slice().sort(function (a, b) { return order.indexOf(a) - order.indexOf(b); })[0];
      Array.prototype.forEach.call(links, function (a) { a.classList.remove("is-active"); });
      if (map[top]) map[top].classList.add("is-active");
    }, { rootMargin: "-72px 0px -70% 0px", threshold: 0 });
    Object.keys(map).forEach(function (id) { io.observe(document.getElementById(id)); });
  });

  /* 5) 사이드바: 현재 항목을 화면 안으로 -------------------------------- */
  guard("sidebar-scroll", function () {
    var cur = document.querySelector(".sidebar .nav a.active");
    if (!cur) return;
    var box = document.querySelector(".sidebar");
    if (!box) return;
    var off = cur.offsetTop - box.clientHeight / 2 + cur.clientHeight / 2;
    if (off > 0) box.scrollTop = off;
  });

  /* 6) 모바일 드로어: 링크 클릭 시 닫기 ---------------------------------- */
  guard("drawer", function () {
    var toggle = document.getElementById("navtoggle");
    if (!toggle) return;
    each(".sidebar .nav a", function (a) {
      a.addEventListener("click", function () { toggle.checked = false; });
    });
  });
})();
