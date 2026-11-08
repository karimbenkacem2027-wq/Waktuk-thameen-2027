"""يضيف بطاقة «تبرع» في صفحة الإعدادات. آمن للتشغيل أكثر من مرة."""
import pathlib
import sys

HTML = pathlib.Path("www/index.html")
MARK = "__donate_card__"
ANCHOR = '+ `<button class="btn o" data-x="adminPanel">'

HEAD = """<style>
/* __donate_card__ */
.don{background:#0A1F33;border:1.5px solid #FFD54A;border-radius:24px;padding:18px;display:flex;flex-direction:column;gap:12px;color:#FAF3E0}
.don h2{color:#2ECC71;font-size:26px;margin:0}
.don p{margin:0;font-size:14px;line-height:1.8;color:#FAF3E0}
.don-row{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:6px 8px;background:rgba(255,213,74,.08);border:1px solid rgba(255,213,74,.35);border-radius:14px;padding:10px 12px}
.don-lbl{font-size:13px;color:#FAF3E0;opacity:.85;flex:1;order:1}
.don-val{color:#FFD54A;font-weight:800;font-size:16px;letter-spacing:.3px;direction:ltr;text-align:left;word-break:break-all;user-select:all;-webkit-user-select:all;flex-basis:100%;order:3}
.don-copy{background:transparent;border:1px solid #2ECC71;color:#2ECC71;border-radius:99px;padding:3px 10px;font:inherit;font-size:12px;font-weight:700;cursor:pointer;flex-shrink:0;order:2}
</style>
<script>
/* __donate_card__ */
function donateCard() {
  var ar = (typeof AR === "function") ? AR() : true;
  var tx = function (a, e) { return ar ? a : e; };
  var row = function (l, v) {
    return '<div class="don-row"><span class="don-lbl">' + l + '</span><span class="don-val">' + v +
      '</span><button class="don-copy" data-copy="' + v + '">' + tx("نسخ", "Copy") + '</button></div>';
  };
  return '<div class="don"><h2>' + tx("تبرع", "Donate") + '</h2>' +
    '<p>' + tx("إن نفعك التطبيق وأردت المساهمة في تطويره مستقبلاً فهذه وسائل التبرع للمطوّر. التبرع اختياري تماماً ولا يؤثر على استخدامك للتطبيق، وجزاك الله خيراً.",
               "If the app helps you and you wish to support its future development, here are the developer's donation details. Donating is entirely optional and does not affect your use of the app.") + '</p>' +
    row("PayPal", "karimbenkacem1@gmail.com") +
    row("RIP", "00799999002698532252") +
    row("CCP", "002698532252") +
    '<div class="don-row"><span class="don-lbl">' + tx("الاسم", "Name") + '</span><span class="don-val">Mr Benkacem Karim</span></div>' +
    '</div>';
}
document.addEventListener("click", function (e) {
  var b = e.target.closest && e.target.closest("[data-copy]");
  if (!b) return;
  var v = b.getAttribute("data-copy");
  var done = function () {
    var o = b.textContent; b.textContent = "✓";
    setTimeout(function () { b.textContent = o; }, 1200);
  };
  var fallback = function () {
    var ta = document.createElement("textarea"); ta.value = v; ta.style.position = "fixed"; ta.style.opacity = "0";
    document.body.appendChild(ta); ta.select();
    try { document.execCommand("copy"); done(); } catch (x) {}
    ta.remove();
  };
  if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(v).then(done, fallback);
  else fallback();
});
</script>
"""

if not HTML.exists():
    sys.exit("www/index.html not found")
h = HTML.read_text(encoding="utf-8")
if MARK in h:
    print("donation card already present")
    sys.exit(0)
if ANCHOR not in h:
    sys.exit("settings anchor not found: www/index.html changed, donation card NOT added")
if "</head>" not in h:
    sys.exit("</head> not found")
h = h.replace(ANCHOR, "+ donateCard()\n    " + ANCHOR, 1)
h = h.replace("</head>", HEAD + "</head>", 1)
HTML.write_text(h, encoding="utf-8")
print("donation card added")
