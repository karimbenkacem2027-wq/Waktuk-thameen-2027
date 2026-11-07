from pathlib import Path
import re, json, shutil
root=Path(__file__).parent
src=root/'index (1).html'
out=root/'www'/'index.html'
out.parent.mkdir(exist_ok=True)
h=src.read_text(encoding='utf-8')
# Clean the visible debug overlay from production builds.
h=re.sub(r'<!-- DEBUG:.*?</script>\s*', '', h, count=1, flags=re.S)
# Manifest is a stable file, not a blob URL (blob service-worker registration is invalid on browsers).
h=h.replace('<link id="manifest-placeholder" rel="manifest">','<link rel="manifest" href="./manifest.webmanifest">')
old='''/* ---------- DYNAMIC PWA SERVICE WORKER & MANIFEST ---------- */
const manifestData = {
  name: "وقتك ثمين | Your Time Is Precious",
  short_name: "وقتك ثمين",
  start_url: "./",
  display: "standalone",
  background_color: "#FAF3E0",
  theme_color: "#0B6B52",
  icons: [
    { src: "https://placehold.co/192x192/0B6B52/FAF3E0?text=وقتك+ثمين", sizes: "192x192", type: "image/png" },
    { src: "https://placehold.co/512x512/0B6B52/FAF3E0?text=وقتك+ثمين", sizes: "512x512", type: "image/png" }
  ]
};
const manifestBlob = new Blob([JSON.stringify(manifestData)], { type: 'application/json' });
document.getElementById('manifest-placeholder').setAttribute('href', URL.createObjectURL(manifestBlob));

let swRegistration = null;
if ('serviceWorker' in navigator) {
  const swCode = `
    const CACHE_NAME = 'yt-pwa-v3';
    self.addEventListener('install', e => e.waitUntil(caches.open(CACHE_NAME).then(c => c.addAll(['./']))));
    self.addEventListener('fetch', e => e.respondWith(caches.match(e.request).then(r => r || fetch(e.request))));
  `;
  const swBlob = new Blob([swCode], { type: 'text/javascript' });
  navigator.serviceWorker.register(URL.createObjectURL(swBlob)).then(reg => {
    swRegistration = reg;
  }).catch(()=>{});
}'''
new='''/* ---------- PWA: stable manifest + installable service worker ---------- */
let swRegistration = null;
if ('serviceWorker' in navigator && location.protocol !== 'file:') {
  navigator.serviceWorker.register('./sw.js').then(reg => { swRegistration = reg; })
    .catch(err => console.info('Service worker unavailable in this environment:', err));
}'''
if old not in h: print('WARN PWA block not found')
else: h=h.replace(old,new)
# Remove flag from header and about card, use a clean brand lockup.
h=h.replace('''    <div class="algeria-flag-container">
      ${DZ_FLAG}
      <span style="font-size:11px;font-weight:700;">الجزائر | Algeria</span>
    </div>
    <h1>وقتك ثمين</h1>''','''    <div class="brand-mark" aria-hidden="true"><span>و</span><i></i></div>
    <h1>وقتك ثمين</h1>''')
h=h.replace('''      <div style="display:flex;align-items:center;gap:6px;margin-top:4px">
        ${DZ_FLAG}
        <span>الجزائر | Algeria</span>
      </div>
''','')
# Contact phone corrected to user's requested number.
h=h.replace('https://wa.me/213778388878','https://wa.me/213778388778').replace('+213 778 38 88 78','+213 778 38 87 78')
# Upgrade onboarding typo and avoid absolute privacy promise.
h=h.replace('بياناتك محفوضة في جهازك، والتطبيق مجاني بالكامل وبدون إعلانات.','تُحفظ إعداداتك وإحصاءاتك محلياً على جهازك. بعض الخدمات مثل جلب المصحف تحتاج إلى اتصال بالإنترنت.')
h=h.replace('Your data stays safe on your device. Totally free & ad-free.','Your settings and statistics are stored locally. Online Quran features require an internet connection.')
# Add premium visual layer before end of style.
css='''
/* ===== V2 premium visual system ===== */
:root { --radius-xl: 24px; --shadow-card: 0 14px 34px rgba(3,24,20,.09); }
body { background: radial-gradient(ellipse at 12% 0%, rgba(212,175,55,.13), transparent 35%), linear-gradient(155deg,var(--bg1),var(--bg2)); }
main { max-width: 560px; padding: 18px 16px 28px; gap: 16px; }
.header-wrapper { padding: 12px 0 4px; gap: 4px; }
.brand-mark { width:58px;height:58px;border-radius:20px;display:grid;place-items:center;position:relative;background:linear-gradient(145deg,#0b6b52,#073b30);border:1px solid rgba(212,175,55,.65);box-shadow:0 10px 24px rgba(4,55,42,.22);margin-bottom:6px; }
.brand-mark span { font:700 36px/1 Amiri,serif;color:#f5d879; }
.brand-mark i { position:absolute; width:7px;height:7px;border-radius:50%;background:#f5d879;top:10px;right:11px;box-shadow:0 0 12px #f5d879; }
h1 { font-size:42px; letter-spacing:-.4px; text-shadow:0 4px 18px rgba(168,132,26,.12); }
.sub { font-size:11px;letter-spacing:.13em;text-transform:uppercase; }
.card { border-radius:var(--radius-xl); padding:18px; box-shadow:var(--shadow-card); backdrop-filter:blur(12px); gap:12px; }
.card h2 { width:100%; text-align:center; }
.verse { font-size:27px; line-height:2; }
.btn { min-height:46px; border-radius:15px; box-shadow:0 5px 14px rgba(7,75,57,.12); }
.btn.o { box-shadow:none; }
.chip { padding:8px 14px; }
.act { border-radius:16px; padding:13px; transition:transform .16s,border-color .16s,background .16s; }
.act:active { transform:scale(.985); }
nav { padding:7px 3px calc(7px + env(safe-area-inset-bottom,0px)); background:color-mix(in srgb,var(--card) 92%,transparent); backdrop-filter:blur(18px); box-shadow:0 -8px 28px rgba(0,0,0,.06); }
nav button { flex:1; min-width:0; font-size:10px; padding:5px 1px; gap:1px; }
nav button svg { width:19px;height:19px; }
.stats { width:100%; }
.quran-toolbar { display:grid;grid-template-columns:1fr auto;gap:8px;width:100%; }
.quran-toolbar select { min-width:0;width:100%;padding:11px;border-radius:13px; }
.ayah { width:100%;padding:14px 12px;border:1px solid var(--ln);border-radius:16px;background:var(--soft);text-align:center; }
.ayah-text { font:24px/2 Amiri,serif; }
.ayah-meta { display:flex;align-items:center;justify-content:space-between;gap:8px;margin-top:8px;font-size:11px;opacity:.75; }
.ayah-play { border:1px solid var(--ln);background:var(--card);color:var(--gold);border-radius:99px;padding:6px 10px;font-size:12px; }
.adhkar-item { width:100%;text-align:start;padding:14px;border:1px solid var(--ln);border-radius:16px;background:var(--soft); }
.adhkar-text { font:22px/1.9 Amiri,serif;text-align:center; }
.adhkar-foot { display:flex;justify-content:space-between;align-items:center;gap:8px;margin-top:10px;font-size:12px; }
.count-pill { border:1px solid var(--gold);border-radius:99px;padding:5px 12px;color:var(--gold);font-weight:800;background:var(--badge-bg); }
button:focus-visible,a:focus-visible,select:focus-visible,input:focus-visible { outline:3px solid var(--gold);outline-offset:3px; }
@media(max-width:380px){ nav button{font-size:9px} nav button svg{width:17px;height:17px} .ayah-text{font-size:21px} }
'''
h=h.replace('</style>',css+'\n</style>',1)
# Extend state and icon map.
h=h.replace('''  settings: `<svg viewBox="0 0 24 24"><path''','''  adhkar: `<svg viewBox="0 0 24 24"><path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm1 5v5.2l3.2 1.9-.9 1.5-4.3-2.6V7z"/></svg>`,
  settings: `<svg viewBox="0 0 24 24"><path''',1)
# Add view definitions before stats.
marker='function stats() {'
insert=r'''const SURAH_NAMES = [
"الفاتحة","البقرة","آل عمران","النساء","المائدة","الأنعام","الأعراف","الأنفال","التوبة","يونس","هود","يوسف","الرعد","إبراهيم","الحجر","النحل","الإسراء","الكهف","مريم","طه","الأنبياء","الحج","المؤمنون","النور","الفرقان","الشعراء","النمل","القصص","العنكبوت","الروم","لقمان","السجدة","الأحزاب","سبأ","فاطر","يس","الصافات","ص","الزمر","غافر","فصلت","الشورى","الزخرف","الدخان","الجاثية","الأحقاف","محمد","الفتح","الحجرات","ق","الذاريات","الطور","النجم","القمر","الرحمن","الواقعة","الحديد","المجادلة","الحشر","الممتحنة","الصف","الجمعة","المنافقون","التغابن","الطلاق","التحريم","الملك","القلم","الحاقة","المعارج","نوح","الجن","المزمل","المدثر","القيامة","الإنسان","المرسلات","النبأ","النازعات","عبس","التكوير","الانفطار","المطففين","الانشقاق","البروج","الطارق","الأعلى","الغاشية","الفجر","البلد","الشمس","الليل","الضحى","الشرح","التين","العلق","القدر","البينة","الزلزلة","العاديات","القارعة","التكاثر","العصر","الهمزة","الفيل","قريش","الماعون","الكوثر","الكافرون","النصر","المسد","الإخلاص","الفلق","الناس"
];
let _quranBusy = false, _quranLoaded = 0;
function quranView() {
  const selected = Math.min(114, Math.max(1, +(S.qSurah || 1)));
  return `<h2>${t("المصحف الشريف","The Noble Quran")}</h2>`
    + card(`<div class="dim">${t("قراءة نص المصحف بالرسم العثماني مع تلاوة الشيخ مشاري العفاسي. يلزم الاتصال بالإنترنت لجلب النص والصوت.","Uthmani Quran text with Mishary Alafasy recitation. Internet is required to load text and audio.")}</div>
      <div class="quran-toolbar"><select id="qSurahSelect" aria-label="${t("اختر السورة","Choose surah")}">${SURAH_NAMES.map((n,i)=>`<option value="${i+1}" ${selected===i+1?"selected":""}>${AR()?n:(i+1)+". "+n}</option>`).join("")}</select><button class="btn sm" data-x="loadQuran">${t("عرض","Open")}</button></div>
      <div id="quranStatus" class="dim" aria-live="polite">${t("اختر سورة لبدء القراءة.","Choose a surah to begin reading.")}</div>
      <div id="quranContent" style="width:100%;display:grid;gap:9px"></div>
      <audio id="quranAudio" controls preload="none" style="width:100%;display:none"></audio>
      <div class="dim">${t("مصدر النص والصوت: AlQuran Cloud API. راجع المصحف المعتمد عند المراجعة والحفظ.","Text and audio provider: AlQuran Cloud API. Consult a verified mushaf when memorizing or checking recitation.")}</div>`);
}
async function loadSurah(n) {
  n = Math.min(114, Math.max(1, Number(n)||1));
  const status = document.getElementById('quranStatus'), box = document.getElementById('quranContent');
  if (!status || !box || _quranBusy) return;
  _quranBusy = true; S.qSurah = n; save();
  status.textContent = t('جارٍ تحميل السورة...','Loading surah...'); box.innerHTML = '';
  try {
    const [tx, au] = await Promise.all([
      fetch(`https://api.alquran.cloud/v1/surah/${n}/quran-uthmani`).then(r=>{if(!r.ok)throw Error('text');return r.json()}),
      fetch(`https://api.alquran.cloud/v1/surah/${n}/ar.alafasy`).then(r=>{if(!r.ok)throw Error('audio');return r.json()})
    ]);
    if (tx.code !== 200 || au.code !== 200) throw Error('api');
    const ayahs = tx.data.ayahs || [], audios = au.data.ayahs || [];
    box.innerHTML = ayahs.map((a,i)=>`<article class="ayah"><div class="ayah-text">${escapeHtml(a.text)}</div><div class="ayah-meta"><span>${t('الآية','Ayah')} ${a.numberInSurah}</span><button class="ayah-play" data-playayah="${escapeAttr(audios[i]?.audio||'')}">▶ ${t('استمع','Listen')}</button></div></article>`).join('');
    status.textContent = `${tx.data.name} • ${tx.data.numberOfAyahs} ${t('آية','ayahs')}`;
    _quranLoaded = n;
  } catch (err) {
    status.textContent = t('تعذر تحميل السورة. تحقق من اتصال الإنترنت ثم أعد المحاولة.','Could not load this surah. Check your internet connection and try again.');
  } finally { _quranBusy = false; }
}
function escapeHtml(s) { return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
function escapeAttr(s) { return escapeHtml(s); }

const ADHKAR = {
 morning: [
  ["أَصْبَحْنَا وَأَصْبَحَ الْمُلْكُ لِلَّهِ، وَالْحَمْدُ لِلَّهِ، لَا إِلَهَ إِلَّا اللَّهُ وَحْدَهُ لَا شَرِيكَ لَهُ...", "مرة واحدة", "صحيح مسلم"],
  ["اللَّهُمَّ بِكَ أَصْبَحْنَا، وَبِكَ أَمْسَيْنَا، وَبِكَ نَحْيَا، وَبِكَ نَمُوتُ، وَإِلَيْكَ النُّشُورُ", "مرة واحدة", "أبو داود والترمذي"],
  ["بِسْمِ اللَّهِ الَّذِي لَا يَضُرُّ مَعَ اسْمِهِ شَيْءٌ فِي الْأَرْضِ وَلَا فِي السَّمَاءِ وَهُوَ السَّمِيعُ الْعَلِيمُ", "ثلاث مرات", "أبو داود والترمذي"],
  ["قُلْ هُوَ اللَّهُ أَحَدٌ، وقُلْ أَعُوذُ بِرَبِّ الْفَلَقِ، وقُلْ أَعُوذُ بِرَبِّ النَّاسِ", "ثلاث مرات لكل سورة", "أبو داود والترمذي"]
 ],
 evening: [
  ["أَمْسَيْنَا وَأَمْسَى الْمُلْكُ لِلَّهِ، وَالْحَمْدُ لِلَّهِ، لَا إِلَهَ إِلَّا اللَّهُ وَحْدَهُ لَا شَرِيكَ لَهُ...", "مرة واحدة", "صحيح مسلم"],
  ["اللَّهُمَّ بِكَ أَمْسَيْنَا، وَبِكَ أَصْبَحْنَا، وَبِكَ نَحْيَا، وَبِكَ نَمُوتُ، وَإِلَيْكَ الْمَصِيرُ", "مرة واحدة", "أبو داود والترمذي"],
  ["بِسْمِ اللَّهِ الَّذِي لَا يَضُرُّ مَعَ اسْمِهِ شَيْءٌ فِي الْأَرْضِ وَلَا فِي السَّمَاءِ وَهُوَ السَّمِيعُ الْعَلِيمُ", "ثلاث مرات", "أبو داود والترمذي"],
  ["قُلْ هُوَ اللَّهُ أَحَدٌ، وقُلْ أَعُوذُ بِرَبِّ الْفَلَقِ، وقُلْ أَعُوذُ بِرَبِّ النَّاسِ", "ثلاث مرات لكل سورة", "أبو داود والترمذي"]
 ]
};
function adhkarView() {
 const period = S.adhkarPeriod || 'morning', list = ADHKAR[period];
 return `<h2>${t('الأذكار اليومية','Daily Adhkar')}</h2>` + card(`<div class="row">${chips('adhkarPeriod', [['morning',t('أذكار الصباح','Morning')],['evening',t('أذكار المساء','Evening')]],period)}</div>
 ${list.map((a,i)=>{const key=period+'_'+i, count=(U.adhkarCounts||{})[key]||0;return `<div class="adhkar-item"><div class="adhkar-text">${a[0]}</div><div class="adhkar-foot"><span>${t(a[1],a[1])} • ${a[2]}</span><button class="count-pill" data-adhkar="${key}">${count} / ${i===2||i===3?3:1} ${t('تسبيح','done')}</button></div></div>`}).join('')}
 <div class="dim">${t('تنبيه: بعض الأذكار عُرضت مختصرة بعلامة الحذف. افتح المصدر للتحقق من اللفظ الكامل، ولا تعتمد على النص المختصر للحفظ.','Some adhkar are intentionally abbreviated with an ellipsis. Consult the cited source for the complete wording before memorizing.')}</div>`);
}

'''
if marker not in h: print('WARN stats marker missing')
else: h=h.replace(marker,insert+marker,1)
# Add navigation routes and Quran tab rendering.
h=h.replace('const v = { home, istighfar: istighfarView, stats, invest, settings }[S.tab] || home;','const v = { home, istighfar: istighfarView, quran: quranView, adhkar: adhkarView, stats, invest, settings }[S.tab] || home;')
h=h.replace('''    ["istighfar", ICONS.istighfar, t("استغفار", "Istighfar")],
    ["stats", ICONS.stats, t("الإحصاءات", "Stats")],''','''    ["quran", ICONS.quran, t("القرآن", "Quran")],
    ["adhkar", ICONS.adhkar, t("الأذكار", "Adhkar")],
    ["istighfar", ICONS.istighfar, t("استغفار", "Istighfar")],
    ["stats", ICONS.stats, t("الإحصاءات", "Stats")],''')
# Load Quran after rendering first time when selected.
h=h.replace('''  ].map(([k, iconSvg, l]) => `<button class="${S.tab === k ? "on" : ""}" data-tab="${k}">${iconSvg}<span>${l}</span></button>`).join("");
}''','''  ].map(([k, iconSvg, l]) => `<button class="${S.tab === k ? "on" : ""}" data-tab="${k}">${iconSvg}<span>${l}</span></button>`).join("");
  if (S.tab === 'quran' && _quranLoaded !== +(S.qSurah||1)) setTimeout(()=>loadSurah(S.qSurah||1), 0);
}''',1)
# Make home Quran entry native tab rather than external website.
h=h.replace('''       <a class="btn s" style="text-decoration:none;display:block;font-weight:700" href="https://quran.com" target="_blank" rel="noopener">${t("افتح المصحف الشريف","Open Quran")}</a>''','''       <button class="btn s" data-tab="quran">${t("افتح المصحف الشريف","Open Quran")}</button>
       <button class="btn s" data-tab="adhkar">${t("أذكار الصباح والمساء","Morning & Evening Adhkar")}</button>''',1)
# Keep stats caveat precise and useful.
h=h.replace('''<div class="dim">${t("ملاحظة: النسخة الشبكية تقيس الوقت الذي تقضيه داخل هذا التطبيق فقط. لاستخدام أعمق، أضف الصفحة لشاشتك الرئيسية.","Note: Web version tracks time spent inside this app page.")}</div>''','''<div class="dim">${t("دقة الإحصاءات: في أندرويد تعتمد متابعة بقية التطبيقات على منح إذن الوصول إلى بيانات الاستخدام. في المتصفح تُحسب مدة بقاء هذه الصفحة مفتوحة فقط.","Tracking note: Android can monitor other apps only after Usage Access is granted. In a browser, only time spent on this page is measured.")}</div>''')
# Add click actions for Quran, adhkar counters and audio; add change handler for surah select.
h=h.replace('''  const D = b.dataset;

  if (D.tab)''','''  const D = b.dataset;

  if (D.playayah) {
    const player = document.getElementById('quranAudio');
    if (player && D.playayah) { player.src = D.playayah; player.style.display = 'block'; player.play().catch(()=>toast(t('تعذر تشغيل الصوت','Audio could not start'),t('اضغط زر التشغيل في مشغل الصوت.','Tap play in the audio player.'))); }
    return;
  }
  if (D.adhkar) {
    U.adhkarCounts = U.adhkarCounts || {}; U.adhkarCounts[D.adhkar] = (U.adhkarCounts[D.adhkar] || 0) + 1; save(); render(); return;
  }
  if (D.tab)''',1)
h=h.replace('''  else if (D.x === "installPWA") {''','''  else if (D.x === "loadQuran") { S.qSurah = +(document.getElementById('qSurahSelect')?.value || 1); _quranLoaded = 0; }
  else if (D.x === "installPWA") {''',1)
# Existing delegated change listener.
h=h.replace('''document.addEventListener("change", e => {
  const i = e.target.dataset;
  if (!i.in) return;''','''document.addEventListener("change", e => {
  if (e.target.id === 'qSurahSelect') { S.qSurah = +e.target.value; _quranLoaded = 0; save(); loadSurah(S.qSurah); return; }
  const i = e.target.dataset;
  if (!i.in) return;''',1)
# Correct typo in existing about page's contact and app name metadata version.
h=h.replace('<meta name="theme-color" content="#0B6B52">','<meta name="theme-color" content="#0B6B52">\n<meta name="color-scheme" content="light dark">\n<meta name="application-name" content="وقتك ثمين V2">')
# Update service worker version and ensure native plugin data sync remains.
# Add manifest/static SW files.
out.write_text(h,encoding='utf-8')
(root/'www'/'manifest.webmanifest').write_text(json.dumps({
 "name":"وقتك ثمين | Your Time Is Precious","short_name":"وقتك ثمين","lang":"ar","dir":"rtl","start_url":"./","scope":"./","display":"standalone","background_color":"#FAF3E0","theme_color":"#0B6B52","description":"رفيقك لحماية الوقت واستثماره في القرآن والذكر والعلم النافع.","icons":[{"src":"./icons/icon-192.png","sizes":"192x192","type":"image/png","purpose":"any maskable"},{"src":"./icons/icon-512.png","sizes":"512x512","type":"image/png","purpose":"any maskable"}]},ensure_ascii=False,indent=2),encoding='utf-8')
(root/'www'/'sw.js').write_text('''const CACHE = 'waqtak-v2-shell';\nconst CORE = ['./','./index.html','./manifest.webmanifest','./icons/icon-192.png','./icons/icon-512.png'];\nself.addEventListener('install', event => { event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(CORE)).then(()=>self.skipWaiting())); });\nself.addEventListener('activate', event => { event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())); });\nself.addEventListener('fetch', event => { const u=new URL(event.request.url); if(u.origin!==location.origin) return; event.respondWith(caches.match(event.request).then(hit=>hit||fetch(event.request).then(res=>{if(res.ok){const copy=res.clone();caches.open(CACHE).then(c=>c.put(event.request,copy));}return res;}).catch(()=>caches.match('./index.html')))); });\n''',encoding='utf-8')
print('Created',out)
