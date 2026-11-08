"""يضيف استقبال إشعارات Firebase (FCM) إلى التطبيق. آمن للتشغيل أكثر من مرة."""
import pathlib
import sys

HTML = pathlib.Path("www/index.html")
MANIFEST = pathlib.Path("android/app/src/main/AndroidManifest.xml")
MARK = "__push_fcm__"

JS = """<script>
/* __push_fcm__ */
(function () {
  var C = window.Capacitor;
  if (!(C && C.isNativePlatform && C.isNativePlatform() && C.registerPlugin)) return;
  var FM;
  try { FM = C.registerPlugin("FirebaseMessaging"); } catch (e) { return; }
  var TOPIC = "all";
  var subscribed = false;

  // عند وصول إشعار والتطبيق مفتوح: يعرضه التطبيق بنفسه (النظام لا يعرضه حينها)
  try {
    Promise.resolve(FM.addListener("notificationReceived", function (ev) {
      try {
        var n = (ev && ev.notification) || {};
        if (typeof toast === "function") toast(n.title || "", n.body || "");
      } catch (e) {}
    })).catch(function () {});
  } catch (e) {}

  // لا نطلب الإذن هنا حتى لا نزعج المستخدم؛ نشترك فقط بعد أن يمنح الإذن من إعدادات التطبيق
  function trySubscribe() {
    if (subscribed) return;
    Promise.resolve(FM.checkPermissions()).then(function (p) {
      if (p && p.receive === "granted") {
        return FM.subscribeToTopic({ topic: TOPIC }).then(function () { subscribed = true; });
      }
    }).catch(function () {});
  }
  trySubscribe();
  document.addEventListener("visibilitychange", function () { if (!document.hidden) trySubscribe(); });
  setInterval(trySubscribe, 30000);
})();
</script>
"""

if not HTML.exists():
    sys.exit("www/index.html not found")
h = HTML.read_text(encoding="utf-8")
if MARK not in h:
    i = h.rfind("</body>")
    if i < 0:
        sys.exit("</body> not found")
    h = h[:i] + JS + h[i:]
    HTML.write_text(h, encoding="utf-8")
print("push script injected")

# أيقونة الإشعار الصغيرة تُضاف فقط إن كانت موجودة فعلاً (حتى لا ينكسر البناء)
icon = pathlib.Path("android/app/src/main/res/drawable-xhdpi/ic_stat_waqt.png")
if MANIFEST.exists() and icon.exists():
    x = MANIFEST.read_text(encoding="utf-8")
    key = "com.google.firebase.messaging.default_notification_icon"
    if key not in x and "</application>" in x:
        meta = '    <meta-data android:name="%s" android:resource="@drawable/ic_stat_waqt" />\n' % key
        x = x.replace("</application>", meta + "</application>", 1)
        MANIFEST.write_text(x, encoding="utf-8")
        print("default notification icon set")
