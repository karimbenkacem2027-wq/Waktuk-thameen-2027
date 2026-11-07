import pathlib, sys

HTML = pathlib.Path("www/index.html")
MANIFEST = pathlib.Path("android/app/src/main/AndroidManifest.xml")

POLY = """<script>
/* __native_notif_poly__ */
(function () {
  var C = window.Capacitor;
  if (!(C && C.isNativePlatform && C.isNativePlatform())) return;
  var LN = C.Plugins && C.Plugins.LocalNotifications;
  if (!LN) return;
  var CH = "reminders";
  var chReady = Promise.resolve(LN.createChannel({
    id: CH, name: "التذكيرات", description: "تذكيرات وقتك ثمين",
    importance: 5, visibility: 1, vibration: true
  })).catch(function () {});
  function map(d) { return d === "granted" ? "granted" : (d === "denied" ? "denied" : "default"); }
  function NativeNotification(title, opts) {
    opts = opts || {};
    var id = 1000 + Math.floor(Math.random() * 2000000000);
    chReady.then(function () {
      return LN.schedule({ notifications: [{
        id: id, title: String(title), body: String(opts.body || ""), channelId: CH
      }] });
    }).catch(function () {});
  }
  NativeNotification.permission = "default";
  NativeNotification.requestPermission = function (cb) {
    return LN.requestPermissions().then(function (r) {
      NativeNotification.permission = map(r.display);
      if (cb) cb(NativeNotification.permission);
      return NativeNotification.permission;
    }).catch(function () { return NativeNotification.permission; });
  };
  window.Notification = NativeNotification;
  LN.checkPermissions().then(function (r) {
    NativeNotification.permission = map(r.display);
    setTimeout(function () { try { if (typeof render === "function") render(); } catch (e) {} }, 300);
  }).catch(function () {});
})();
</script>
"""

SCHED = """<script>
/* __native_notif_sched__ */
(function () {
  var C = window.Capacitor;
  if (!(C && C.isNativePlatform && C.isNativePlatform())) return;
  var LN = C.Plugins && C.Plugins.LocalNotifications;
  if (!LN) return;
  var CH = "reminders";
  var DELAY = 4000;
  var tracked = { 7001: 0, 7002: 0 };

  function ar() { try { return typeof AR === "function" ? AR() : true; } catch (e) { return true; } }

  function sync(id, end, title, body) {
    if (end === tracked[id]) return;
    if (end > 0) {
      if (window.Notification.permission !== "granted") return;
      tracked[id] = end;
      LN.cancel({ notifications: [{ id: id }] }).catch(function () {}).then(function () {
        return LN.schedule({ notifications: [{
          id: id, title: title, body: body, channelId: CH,
          schedule: { at: new Date(end + DELAY), allowWhileIdle: true }
        }] });
      }).catch(function () {});
    } else {
      tracked[id] = 0;
      LN.cancel({ notifications: [{ id: id }] }).catch(function () {});
    }
  }

  setInterval(function () {
    try {
      var se = typeof sessEnd !== "undefined" ? sessEnd : 0;
      var ie = typeof istighfarEnd !== "undefined" ? istighfarEnd : 0;
      var m = typeof sessMin !== "undefined" ? Math.round(sessMin) : 0;
      sync(7001, se,
        ar() ? "تقبّل الله منك 🌿" : "May Allah accept it 🌿",
        ar() ? "أتممت " + m + " دقيقة في عمل نافع. بارك الله فيك." : "You completed " + m + " minutes of beneficial activity.");
      sync(7002, ie,
        ar() ? "تقبّل الله استغفارك" : "May Allah Accept Your Istighfar",
        ar() ? "انتهت جلسة الاستغفار. جعله الله في ميزان حسناتك." : "Your Istighfar session has ended.");
    } catch (e) {}
  }, 1000);
})();
</script>
"""

if not HTML.exists():
    sys.exit("www/index.html not found")
h = HTML.read_text(encoding="utf-8")

h = h.replace('Capacitor.registerPlugin("UsageMonitor")', "(Capacitor.Plugins.UsageMonitor || null)")

if "__native_notif_poly__" not in h:
    if "</head>" not in h or "</body>" not in h:
        sys.exit("anchors </head> or </body> not found")
    h = h.replace("</head>", POLY + "</head>", 1)
    i = h.rfind("</body>")
    h = h[:i] + SCHED + h[i:]
HTML.write_text(h, encoding="utf-8")
print("html patched")

if MANIFEST.exists():
    x = MANIFEST.read_text(encoding="utf-8")
    perms = ["android.permission.POST_NOTIFICATIONS", "android.permission.VIBRATE"]
    add = "".join('    <uses-permission android:name="%s" />\n' % p for p in perms if p not in x)
    if add:
        x = x.replace("</manifest>", add + "</manifest>")
        MANIFEST.write_text(x, encoding="utf-8")
    print("manifest patched")
else:
    sys.exit("AndroidManifest.xml not found")
