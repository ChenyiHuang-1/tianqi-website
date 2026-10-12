// Tianqi Materials site script: menu, product dropdown, filters, pattern library, inquiry form.
(function () {
  var lang = document.body.dataset.lang;
  var zh = lang === "zh";

  // ---- current section in nav
  var section = document.body.dataset.section;
  document.querySelectorAll("[data-nav]").forEach(function (a) {
    if (a.dataset.nav === section) a.setAttribute("aria-current", "page");
  });

  // ---- mobile menu
  var mb = document.getElementById("menu-btn"), menu = document.getElementById("menu");
  if (mb) mb.addEventListener("click", function () {
    var open = menu.classList.toggle("open");
    mb.setAttribute("aria-expanded", open);
  });

  // ---- products dropdown (click or keyboard; hover handled in CSS on desktop)
  document.querySelectorAll(".has-drop").forEach(function (li) {
    var btn = li.querySelector(".drop-btn");
    function set(open) { li.classList.toggle("open", open); btn.setAttribute("aria-expanded", open); }
    btn.addEventListener("click", function (e) { e.stopPropagation(); set(!li.classList.contains("open")); });
    li.addEventListener("keydown", function (e) { if (e.key === "Escape") { set(false); btn.focus(); } });
    document.addEventListener("click", function (e) { if (!li.contains(e.target)) set(false); });
    li.addEventListener("focusout", function (e) { if (!li.contains(e.relatedTarget)) set(false); });
  });

  // ---- chip filters (category pages and pattern library)
  function chipState(bar) {
    var st = {};
    bar.querySelectorAll(".chips").forEach(function (g) {
      var on = g.querySelector('.chip[aria-pressed="true"]');
      st[g.dataset.f] = on ? on.dataset.v : "";
    });
    return st;
  }
  function matches(el, st) {
    for (var k in st) if (st[k] && el.dataset[k] !== st[k]) return false;
    return true;
  }
  document.querySelectorAll(".filter-bar").forEach(function (bar) {
    bar.addEventListener("click", function (e) {
      var c = e.target.closest(".chip"); if (!c) return;
      c.parentNode.querySelectorAll(".chip").forEach(function (x) { x.setAttribute("aria-pressed", x === c); });
      bar.dispatchEvent(new Event("change"));
    });
  });

  // category page: filter product cards, hide empty sub-sections
  var prodGrid = document.getElementById("prod-grid");
  var prodBar = document.querySelector('[data-filter-target="prod-grid"]');
  if (prodGrid && prodBar) prodBar.addEventListener("change", function () {
    var st = chipState(prodBar);
    prodGrid.querySelectorAll(".sub").forEach(function (sec) {
      var cards = sec.querySelectorAll(".prod"), shown = 0;
      cards.forEach(function (c) { var ok = matches(c, st); c.hidden = !ok; if (ok) shown++; });
      sec.hidden = cards.length > 0 && shown === 0;
      if (cards.length === 0) sec.hidden = Object.keys(st).some(function (k) { return st[k]; });
    });
  });

  // pattern library: number search, verified tags, load more
  var grid = document.getElementById("grid");
  if (grid) {
    var cards = Array.prototype.slice.call(grid.querySelectorAll(".pcard"));
    var size = +grid.dataset.pageSize || 48, limit = size, q = "";
    var libBar = document.querySelector('[data-filter-target="grid"]');
    var more = document.getElementById("more"), count = document.getElementById("count");
    function apply() {
      var st = libBar ? chipState(libBar) : {}, n = 0;
      cards.forEach(function (c) {
        var ok = matches(c, st) && (!q || c.dataset.id.indexOf(q) !== -1);
        if (ok) n++;
        c.hidden = !ok || n > limit;
      });
      count.textContent = zh ? ("共 " + n + " 款") : (n + (n === 1 ? " pattern" : " patterns"));
      more.hidden = n <= limit;
    }
    document.getElementById("q").addEventListener("input", function (e) { q = e.target.value.replace(/\D/g, ""); limit = size; apply(); });
    more.addEventListener("click", function () { limit += size; apply(); });
    if (libBar) libBar.addEventListener("change", function () { limit = size; apply(); });
    apply();
  }

  // pattern detail: switch views
  var mainView = document.getElementById("main-view");
  document.querySelectorAll("[data-view]").forEach(function (b) {
    b.addEventListener("click", function () { mainView.src = b.dataset.view; });
  });

  // ---- inquiry form
  var form = document.getElementById("inquiry");
  if (!form) return;
  var params = new URLSearchParams(location.search);
  var endpoint = form.dataset.endpoint;
  var type = params.get("type");
  if (type) {
    var r = form.querySelector('input[name="inquiry_type"][value="' + type + '"]');
    if (r) r.checked = true;
  }
  var codes = [];
  if (params.get("product")) codes.push(params.get("product"));
  if (params.get("pattern")) codes.push((zh ? "纹样 " : "Pattern ") + params.get("pattern"));
  if (codes.length) document.getElementById("f-codes").value = codes.join(", ");
  function showFields() {
    var t = form.querySelector('input[name="inquiry_type"]:checked').value;
    form.querySelectorAll("[data-for]").forEach(function (el) {
      el.hidden = el.dataset.for.split(" ").indexOf(t) === -1;
    });
  }
  form.addEventListener("change", function (e) { if (e.target.name === "inquiry_type") showFields(); });
  showFields();
  var fileField = form.querySelector("[data-files-only]");
  if (fileField) fileField.hidden = !(endpoint && form.dataset.files);
  var btn = form.querySelector('button[type="submit"]');
  if (!endpoint) {
    btn.disabled = true;
    document.getElementById("form-off").hidden = false;
  }

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var msg = document.getElementById("form-msg");
    msg.className = "form-msg full";
    var data = new FormData(form);
    if (data.get("website")) return; // spam trap
    var name = (data.get("name") || "").trim(), email = (data.get("email") || "").trim(), need = (data.get("message") || "").trim();
    if (!name || !need || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
      msg.classList.add("err");
      msg.textContent = zh ? "请填写联系人、有效邮箱和需求说明。" : "Please fill in your name, a valid email and your requirement.";
      return;
    }
    if (!endpoint) return;
    data.append("page_language", lang);
    data.append("page_url", location.href);
    data.append("_subject", "Website inquiry from " + name);
    data.append("_template", "table");
    btn.disabled = true;
    fetch(endpoint, { method: "POST", body: data, headers: { Accept: "application/json" } })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json().catch(function () { return {}; });
      })
      .then(function (j) {
        if (j && j.success === false) throw new Error(j.message || "rejected");
        msg.classList.add("ok");
        msg.textContent = zh ? "已收到您的需求，我们会尽快回复。" : "Thank you. We have received your inquiry and will reply soon.";
        form.reset(); showFields();
      })
      .catch(function () {
        msg.classList.add("err");
        msg.textContent = zh ? "提交没有成功，请稍后再试。" : "Your inquiry was not sent. Please try again.";
      })
      .finally(function () { btn.disabled = false; });
  });
})();

// ---- home pattern carousel: arrows, dots, swipe (native scroll), auto-advance paused on hover/focus
(function () {
  document.querySelectorAll("[data-carousel]").forEach(function (c) {
    var track = c.querySelector(".car-track"), pages = c.querySelectorAll(".car-page"), dots = c.querySelectorAll(".car-dot");
    var n = pages.length, cur = 0, hold = false;
    function mark() {
      cur = Math.round(track.scrollLeft / track.clientWidth);
      dots.forEach(function (d, i) { d.setAttribute("aria-current", i === cur ? "true" : "false"); });
    }
    function go(i) { track.scrollTo({ left: ((i + n) % n) * track.clientWidth }); }
    c.querySelector(".prev").addEventListener("click", function () { go(cur - 1); });
    c.querySelector(".next").addEventListener("click", function () { go(cur + 1); });
    dots.forEach(function (d, i) { d.addEventListener("click", function () { go(i); }); });
    track.addEventListener("scroll", function () { window.requestAnimationFrame(mark); });
    ["mouseenter", "focusin", "touchstart"].forEach(function (ev) { c.addEventListener(ev, function () { hold = true; }, { passive: true }); });
    ["mouseleave", "focusout"].forEach(function (ev) { c.addEventListener(ev, function () { hold = false; }); });
    var still = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!still) setInterval(function () { if (!hold && !document.hidden) go(cur + 1); }, 6000);
    mark();
  });
})();
