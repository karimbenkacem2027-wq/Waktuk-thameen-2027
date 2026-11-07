import json, os, pathlib, sys

CFG = pathlib.Path("capacitor.config.json")
HTML = pathlib.Path("www/index.html")
MANIFEST = pathlib.Path("android/app/src/main/AndroidManifest.xml")
RES = pathlib.Path("android/app/src/main/res")

cfg = json.loads(CFG.read_text(encoding="utf-8"))
PKG = cfg["appId"]
JAVA_DIR = pathlib.Path("android/app/src/main/java") / PKG.replace(".", "/")
JAVA_DIR.mkdir(parents=True, exist_ok=True)


def J(s):
    """Escape text so it is safe inside a Java string literal (ASCII only)."""
    out = []
    for ch in s:
        if ch == "\n":
            out.append("\\n")
        elif ch == '"':
            out.append('\\"')
        elif ord(ch) < 128:
            out.append(ch)
        else:
            b = ch.encode("utf-16-be")
            for i in range(0, len(b), 2):
                out.append("\\u%02x%02x" % (b[i], b[i + 1]))
    return "".join(out)


TEXTS = {
    "PKG": PKG,
    "TITLE_AR": J("وقتك ثمين"),
    "TITLE_EN": J("Your Time Is Precious"),
    "CH_AR": J("تذكيرات الوقت"),
    "TOT_AR_A": J("مرّت "),
    "TOT_AR_B": J(" من وقتك على الشاشة! 🌿\nتذكّر أن الوقت أمانة، فاجعل منه نصيباً للقرآن والعلم."),
    "TOT_EN_B": J(" passed on your screen! 🌿\nRemember, your time is precious. Give some of it to the Quran and learning."),
    "CONT_AR_B": J(" من الاستخدام المتواصل.\nخذ استراحة من الشاشة، وامنح قلبك بعض الوقت مع الذكر."),
    "CONT_EN_B": J(" of continuous use have passed.\nTake a break from the screen and refresh your heart."),
    "MIN_AR": J(" دقيقة"),
    "HOUR1": J("ساعة"),
    "HOUR2": J("ساعتان"),
    "HOURS_AR": J(" ساعات"),
    "HOUR_AR": J(" ساعة"),
}


def render(tpl):
    for k, v in TEXTS.items():
        tpl = tpl.replace("@@" + k + "@@", v)
    return tpl


MONITOR = r'''package @@PKG@@;

import android.app.AlarmManager;
import android.app.AppOpsManager;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.usage.UsageEvents;
import android.app.usage.UsageStatsManager;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.content.pm.ResolveInfo;
import android.os.Build;
import android.os.PowerManager;
import android.os.Process;
import android.os.SystemClock;
import androidx.core.app.NotificationCompat;
import androidx.core.app.NotificationManagerCompat;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.json.JSONObject;

public final class UsageMonitor {
    private UsageMonitor() {}

    static final String PREFS = "yt_native";
    static final int ALARM_CODE = 4242;

    public static final class Result {
        public long totalSec;
        public long contSec;
        public long contStart;
        public ArrayList<Object[]> top = new ArrayList<Object[]>();
    }

    static SharedPreferences prefs(Context c) {
        return c.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    static JSONObject cfg(Context c) {
        try {
            return new JSONObject(prefs(c).getString("cfg", "{}"));
        } catch (Exception e) {
            return new JSONObject();
        }
    }

    static boolean flag(JSONObject o, String k, boolean def) {
        if (!o.has(k)) return def;
        Object v = o.opt(k);
        if (v instanceof Boolean) return ((Boolean) v).booleanValue();
        if (v instanceof Number) return ((Number) v).intValue() != 0;
        return def;
    }

    static int breakMin(Context c) {
        return Math.max(1, cfg(c).optInt("breakMin", 5));
    }

    /* ---------- permissions ---------- */

    static boolean hasUsageAccess(Context c) {
        try {
            AppOpsManager a = (AppOpsManager) c.getSystemService(Context.APP_OPS_SERVICE);
            int mode;
            if (Build.VERSION.SDK_INT >= 29) {
                mode = a.unsafeCheckOpNoThrow(AppOpsManager.OPSTR_GET_USAGE_STATS, Process.myUid(), c.getPackageName());
            } else {
                mode = a.checkOpNoThrow(AppOpsManager.OPSTR_GET_USAGE_STATS, Process.myUid(), c.getPackageName());
            }
            if (mode == AppOpsManager.MODE_DEFAULT) {
                return c.checkCallingOrSelfPermission("android.permission.PACKAGE_USAGE_STATS") == PackageManager.PERMISSION_GRANTED;
            }
            return mode == AppOpsManager.MODE_ALLOWED;
        } catch (Throwable t) {
            return false;
        }
    }

    static boolean notifEnabled(Context c) {
        try {
            return NotificationManagerCompat.from(c).areNotificationsEnabled();
        } catch (Throwable t) {
            return false;
        }
    }

    /* ---------- usage computation ---------- */

    private static Set<String> skipPackages(Context c) {
        Set<String> s = new HashSet<String>();
        s.add("com.android.systemui");
        s.add("android");
        try {
            Intent h = new Intent(Intent.ACTION_MAIN);
            h.addCategory(Intent.CATEGORY_HOME);
            List<ResolveInfo> l = c.getPackageManager().queryIntentActivities(h, 0);
            for (ResolveInfo r : l) {
                if (r.activityInfo != null) s.add(r.activityInfo.packageName);
            }
        } catch (Throwable t) {
        }
        return s;
    }

    private static void close(ArrayList<long[]> iv, HashMap<String, Long> per, String p, long s, long e) {
        if (e <= s) return;
        iv.add(new long[] {s, e});
        Long old = per.get(p);
        per.put(p, (old == null ? 0L : old.longValue()) + (e - s));
    }

    private static String label(PackageManager pm, String pkg) {
        try {
            return String.valueOf(pm.getApplicationLabel(pm.getApplicationInfo(pkg, 0)));
        } catch (Throwable t) {
            int i = pkg.lastIndexOf('.');
            return i >= 0 ? pkg.substring(i + 1) : pkg;
        }
    }

    static Result compute(Context c, int breakMin) {
        Result r = new Result();
        UsageStatsManager usm = (UsageStatsManager) c.getSystemService(Context.USAGE_STATS_SERVICE);
        if (usm == null) return r;

        long now = System.currentTimeMillis();
        Calendar cal = Calendar.getInstance();
        cal.set(Calendar.HOUR_OF_DAY, 0);
        cal.set(Calendar.MINUTE, 0);
        cal.set(Calendar.SECOND, 0);
        cal.set(Calendar.MILLISECOND, 0);
        long dayStart = cal.getTimeInMillis();

        Set<String> skip = skipPackages(c);
        UsageEvents events = usm.queryEvents(dayStart, now);
        UsageEvents.Event e = new UsageEvents.Event();
        ArrayList<long[]> iv = new ArrayList<long[]>();
        HashMap<String, Long> per = new HashMap<String, Long>();
        String cur = null;
        long curSince = 0;

        while (events != null && events.hasNextEvent()) {
            events.getNextEvent(e);
            int type = e.getEventType();
            long ts = e.getTimeStamp();
            String p = e.getPackageName();
            if (type == 1) {
                boolean skipped = skip.contains(p);
                if (cur != null && (skipped || !cur.equals(p))) {
                    close(iv, per, cur, curSince, ts);
                    cur = null;
                }
                if (!skipped && cur == null) {
                    cur = p;
                    curSince = ts;
                }
            } else if (type == 2) {
                if (cur != null && cur.equals(p)) {
                    close(iv, per, cur, curSince, ts);
                    cur = null;
                }
            } else if (type == 16 || type == 17 || type == 26) {
                if (cur != null) {
                    close(iv, per, cur, curSince, ts);
                    cur = null;
                }
            }
        }
        if (cur != null) {
            PowerManager pw = (PowerManager) c.getSystemService(Context.POWER_SERVICE);
            boolean on = pw == null || pw.isInteractive();
            if (on) close(iv, per, cur, curSince, now);
        }

        long breakMs = breakMin * 60000L;
        long total = 0, active = 0, sessStart = 0, prevEnd = 0;
        for (int i = 0; i < iv.size(); i++) {
            long[] x = iv.get(i);
            total += x[1] - x[0];
            if (i == 0 || x[0] - prevEnd >= breakMs) {
                sessStart = x[0];
                active = 0;
            }
            active += x[1] - x[0];
            prevEnd = x[1];
        }
        r.totalSec = total / 1000;
        if (!iv.isEmpty() && now - prevEnd < breakMs) {
            r.contSec = active / 1000;
            r.contStart = sessStart;
        }

        ArrayList<Map.Entry<String, Long>> list = new ArrayList<Map.Entry<String, Long>>(per.entrySet());
        Collections.sort(list, (a, b) -> Long.compare(b.getValue().longValue(), a.getValue().longValue()));
        PackageManager pm = c.getPackageManager();
        for (Map.Entry<String, Long> en : list) {
            if (r.top.size() >= 5) break;
            if (en.getValue().longValue() < 60000L) break;
            r.top.add(new Object[] {label(pm, en.getKey()), Long.valueOf(en.getValue().longValue() / 1000)});
        }
        return r;
    }

    /* ---------- reminders ---------- */

    static boolean isQuiet(JSONObject cfg) {
        if (!flag(cfg, "quietOn", true)) return false;
        Calendar n = Calendar.getInstance();
        int m = n.get(Calendar.HOUR_OF_DAY) * 60 + n.get(Calendar.MINUTE);
        int a = hm(cfg.optString("qs", "22:00"));
        int b = hm(cfg.optString("qe", "05:00"));
        return a <= b ? (m >= a && m < b) : (m >= a || m < b);
    }

    private static int hm(String s) {
        try {
            return Integer.parseInt(s.substring(0, 2)) * 60 + Integer.parseInt(s.substring(3, 5));
        } catch (Exception e) {
            return 0;
        }
    }

    private static String dateKey() {
        Calendar n = Calendar.getInstance();
        return n.get(Calendar.YEAR) + "-" + (n.get(Calendar.MONTH) + 1) + "-" + n.get(Calendar.DAY_OF_MONTH);
    }

    private static String durAr(int m) {
        if (m % 60 != 0) return m + "@@MIN_AR@@";
        int h = m / 60;
        if (h == 1) return "@@HOUR1@@";
        if (h == 2) return "@@HOUR2@@";
        if (h <= 10) return h + "@@HOURS_AR@@";
        return h + "@@HOUR_AR@@";
    }

    private static String durEn(int m) {
        if (m % 60 != 0) return m + " minutes";
        if (m == 60) return "One hour";
        return (m / 60) + " hours";
    }

    static synchronized void maybeNotify(Context c, Result r) {
        JSONObject cfg = cfg(c);
        SharedPreferences sp = prefs(c);
        String today = dateKey();
        int tb = sp.getInt("tb", 0);
        long cs = sp.getLong("cs", 0L);
        int cb = sp.getInt("cb", 0);
        if (!today.equals(sp.getString("day", ""))) {
            tb = 0;
            cs = 0L;
            cb = 0;
        }
        boolean quiet = isQuiet(cfg);
        boolean ar = !"en".equals(cfg.optString("lang", "ar"));
        boolean vib = flag(cfg, "vib", true);

        if (flag(cfg, "totalOn", true)) {
            int tm = Math.max(1, cfg.optInt("totalMin", 240));
            int b = (int) (r.totalSec / 60 / tm);
            if (b > tb) {
                tb = b;
                if (!quiet) show(c, ar, vib, true, b * tm);
            }
        }
        if (flag(cfg, "contOn", true)) {
            int cm = Math.max(1, cfg.optInt("contMin", 120));
            if (r.contStart != cs) {
                cs = r.contStart;
                cb = 0;
            }
            int b = (int) (r.contSec / 60 / cm);
            if (b > cb) {
                cb = b;
                if (!quiet) show(c, ar, vib, false, b * cm);
            }
        }
        sp.edit().putString("day", today).putInt("tb", tb).putLong("cs", cs).putInt("cb", cb).apply();
    }

    private static void show(Context c, boolean ar, boolean vib, boolean total, int min) {
        try {
            String title = ar ? "@@TITLE_AR@@" : "@@TITLE_EN@@";
            String body;
            if (total) {
                body = ar ? ("@@TOT_AR_A@@" + durAr(min) + "@@TOT_AR_B@@") : (durEn(min) + "@@TOT_EN_B@@");
            } else {
                body = ar ? ("@@TOT_AR_A@@" + durAr(min) + "@@CONT_AR_B@@") : (durEn(min) + "@@CONT_EN_B@@");
            }
            String chId = vib ? "yt_remind_vib" : "yt_remind_quiet";
            if (Build.VERSION.SDK_INT >= 26) {
                NotificationManager nm = (NotificationManager) c.getSystemService(Context.NOTIFICATION_SERVICE);
                if (nm != null && nm.getNotificationChannel(chId) == null) {
                    NotificationChannel ch = new NotificationChannel(chId, "@@CH_AR@@", NotificationManager.IMPORTANCE_HIGH);
                    ch.enableVibration(vib);
                    nm.createNotificationChannel(ch);
                }
            }
            int icon = c.getResources().getIdentifier("ic_stat_waqt", "drawable", c.getPackageName());
            if (icon == 0) icon = android.R.drawable.ic_dialog_info;

            NotificationCompat.Builder b = new NotificationCompat.Builder(c, chId)
                    .setSmallIcon(icon)
                    .setContentTitle(title)
                    .setContentText(body.split("\n")[0])
                    .setStyle(new NotificationCompat.BigTextStyle().bigText(body))
                    .setPriority(NotificationCompat.PRIORITY_HIGH)
                    .setCategory(NotificationCompat.CATEGORY_REMINDER)
                    .setAutoCancel(true);
            if (vib) b.setVibrate(new long[] {0, 200, 100, 200});
            Intent open = c.getPackageManager().getLaunchIntentForPackage(c.getPackageName());
            if (open != null) {
                b.setContentIntent(PendingIntent.getActivity(c, 0, open, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE));
            }
            if (!notifEnabled(c)) return;
            NotificationManagerCompat.from(c).notify(total ? 9001 : 9002, b.build());
        } catch (Throwable t) {
        }
    }

    /* ---------- background scheduling ---------- */

    private static Intent alarmIntent(Context c) {
        Intent i = new Intent(c, AlarmReceiver.class);
        i.setAction("@@PKG@@.CHECK");
        return i;
    }

    static void ensureScheduled(Context c) {
        PendingIntent existing = PendingIntent.getBroadcast(c, ALARM_CODE, alarmIntent(c), PendingIntent.FLAG_NO_CREATE | PendingIntent.FLAG_IMMUTABLE);
        if (existing == null) scheduleIn(c, 60000L);
    }

    static void scheduleIn(Context c, long ms) {
        try {
            AlarmManager am = (AlarmManager) c.getSystemService(Context.ALARM_SERVICE);
            PendingIntent pi = PendingIntent.getBroadcast(c, ALARM_CODE, alarmIntent(c), PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
            long at = SystemClock.elapsedRealtime() + ms;
            if (Build.VERSION.SDK_INT >= 23) {
                am.setAndAllowWhileIdle(AlarmManager.ELAPSED_REALTIME_WAKEUP, at, pi);
            } else {
                am.set(AlarmManager.ELAPSED_REALTIME_WAKEUP, at, pi);
            }
        } catch (Throwable t) {
        }
    }
}
'''

PLUGIN = r'''package @@PKG@@;

import android.Manifest;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.net.Uri;
import android.os.Build;
import android.provider.Settings;
import androidx.core.app.ActivityCompat;
import com.getcapacitor.JSArray;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

@CapacitorPlugin(name = "UsageMonitor")
public class UsageMonitorPlugin extends Plugin {

    @PluginMethod
    public void hasPermission(PluginCall call) {
        Context c = getContext();
        JSObject o = new JSObject();
        o.put("usage", UsageMonitor.hasUsageAccess(c));
        o.put("notif", UsageMonitor.notifEnabled(c));
        call.resolve(o);
    }

    @PluginMethod
    public void openUsageSettings(PluginCall call) {
        Context c = getContext();
        try {
            Intent i = new Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS);
            i.setData(Uri.parse("package:" + c.getPackageName()));
            i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            c.startActivity(i);
        } catch (Exception e1) {
            try {
                Intent i = new Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS);
                i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                c.startActivity(i);
            } catch (Exception e2) {
            }
        }
        call.resolve();
    }

    @PluginMethod
    public void requestNotif(PluginCall call) {
        Context c = getContext();
        if (UsageMonitor.notifEnabled(c)) {
            call.resolve();
            return;
        }
        SharedPreferences sp = UsageMonitor.prefs(c);
        boolean asked = sp.getBoolean("asked", false);
        try {
            if (Build.VERSION.SDK_INT >= 33 && !asked) {
                sp.edit().putBoolean("asked", true).apply();
                ActivityCompat.requestPermissions(getActivity(), new String[] {Manifest.permission.POST_NOTIFICATIONS}, 7711);
            } else {
                Intent i = new Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS);
                i.putExtra(Settings.EXTRA_APP_PACKAGE, c.getPackageName());
                i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                c.startActivity(i);
            }
        } catch (Exception e) {
        }
        call.resolve();
    }

    @PluginMethod
    public void saveConfig(PluginCall call) {
        String cfg = call.getString("cfg");
        if (cfg != null) {
            UsageMonitor.prefs(getContext()).edit().putString("cfg", cfg).apply();
        }
        call.resolve();
    }

    @PluginMethod
    public void start(PluginCall call) {
        UsageMonitor.ensureScheduled(getContext());
        call.resolve();
    }

    @PluginMethod
    public void getUsage(PluginCall call) {
        Context c = getContext();
        try {
            UsageMonitor.Result r = UsageMonitor.compute(c, UsageMonitor.breakMin(c));
            UsageMonitor.maybeNotify(c, r);
            JSObject o = new JSObject();
            o.put("sec", r.totalSec);
            JSArray top = new JSArray();
            for (Object[] a : r.top) {
                JSObject x = new JSObject();
                x.put("name", (String) a[0]);
                x.put("sec", ((Long) a[1]).longValue());
                top.put(x);
            }
            o.put("top", top);
            call.resolve(o);
        } catch (Exception e) {
            call.reject("usage error");
        }
    }
}
'''

ALARM = r'''package @@PKG@@;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.PowerManager;

public class AlarmReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context c, Intent intent) {
        if (!UsageMonitor.hasUsageAccess(c)) return;
        try {
            UsageMonitor.Result r = UsageMonitor.compute(c, UsageMonitor.breakMin(c));
            UsageMonitor.maybeNotify(c, r);
        } catch (Throwable t) {
        }
        PowerManager pm = (PowerManager) c.getSystemService(Context.POWER_SERVICE);
        boolean on = pm == null || pm.isInteractive();
        UsageMonitor.scheduleIn(c, on ? 60000L : 600000L);
    }
}
'''

BOOT = r'''package @@PKG@@;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

public class BootReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context c, Intent intent) {
        if (UsageMonitor.hasUsageAccess(c)) {
            UsageMonitor.scheduleIn(c, 120000L);
        }
    }
}
'''

MAIN = r'''package @@PKG@@;

import android.os.Bundle;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(UsageMonitorPlugin.class);
        super.onCreate(savedInstanceState);
    }
}
'''

for name, tpl in [
    ("UsageMonitor.java", MONITOR),
    ("UsageMonitorPlugin.java", PLUGIN),
    ("AlarmReceiver.java", ALARM),
    ("BootReceiver.java", BOOT),
    ("MainActivity.java", MAIN),
]:
    (JAVA_DIR / name).write_text(render(tpl), encoding="utf-8")
print("java files written to", JAVA_DIR)

# ---------- AndroidManifest ----------
if not MANIFEST.exists():
    sys.exit("AndroidManifest.xml not found")
x = MANIFEST.read_text(encoding="utf-8")
if "AlarmReceiver" not in x:
    perms = [
        "android.permission.PACKAGE_USAGE_STATS",
        "android.permission.RECEIVE_BOOT_COMPLETED",
        "android.permission.POST_NOTIFICATIONS",
        "android.permission.VIBRATE",
    ]
    add = "".join('    <uses-permission android:name="%s" />\n' % p for p in perms if p not in x)
    recv = (
        '        <receiver android:name="%s.AlarmReceiver" android:exported="false" />\n'
        '        <receiver android:name="%s.BootReceiver" android:exported="true">\n'
        '            <intent-filter>\n'
        '                <action android:name="android.intent.action.BOOT_COMPLETED" />\n'
        '                <action android:name="android.intent.action.MY_PACKAGE_REPLACED" />\n'
        '            </intent-filter>\n'
        '        </receiver>\n'
    ) % (PKG, PKG)
    if "</application>" not in x or "</manifest>" not in x:
        sys.exit("manifest anchors not found")
    x = x.replace("</application>", recv + "    </application>", 1)
    x = x.replace("</manifest>", add + "</manifest>", 1)
    MANIFEST.write_text(x, encoding="utf-8")
print("manifest patched")

# ---------- notification small icon (white silhouette) ----------
try:
    from PIL import Image
    src = next(f for f in sorted(os.listdir(".")) if f.lower().endswith(".png"))
    im = Image.open(src).convert("RGBA")
    px = im.load()
    w, h = im.size
    for yy in range(h):
        for xx in range(w):
            r, g, b, a = px[xx, yy]
            lum = 0.299 * r + 0.587 * g + 0.114 * b
            if a > 0 and lum > 140 and not (abs(r - g) < 14 and abs(g - b) < 14 and r < 160 and r > 95 and (xx < w * 0.2 or xx > w * 0.8)):
                px[xx, yy] = (255, 255, 255, 255)
            else:
                px[xx, yy] = (255, 255, 255, 0)
    bbox = im.getchannel("A").getbbox()
    if bbox:
        im = im.crop(bbox)
        side = max(im.size)
        sq = Image.new("RGBA", (side, side), (255, 255, 255, 0))
        sq.paste(im, ((side - im.width) // 2, (side - im.height) // 2))
        for d, s in {"mdpi": 24, "hdpi": 36, "xhdpi": 48, "xxhdpi": 72, "xxxhdpi": 96}.items():
            folder = RES / ("drawable-" + d)
            folder.mkdir(parents=True, exist_ok=True)
            sq.resize((s, s), Image.LANCZOS).save(folder / "ic_stat_waqt.png")
        print("small icons written")
except Exception as ex:
    print("small icon skipped:", ex)

# ---------- capacitor config: use the small icon for local notifications ----------
cfg.setdefault("plugins", {})["LocalNotifications"] = {"smallIcon": "ic_stat_waqt", "iconColor": "#0B6B52"}
CFG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")

# ---------- JS: plugin proxy fallback (runs first in <head>) ----------
FALLBACK = """<script>
/* __plugin_fallback__ */
(function () {
  try {
    var C = window.Capacitor;
    if (!(C && C.isNativePlatform && C.isNativePlatform())) return;
    C.Plugins = C.Plugins || {};
    ["LocalNotifications", "UsageMonitor"].forEach(function (n) {
      if (C.Plugins[n] || typeof C.nativePromise !== "function") return;
      C.Plugins[n] = new Proxy({}, { get: function (_, m) {
        if (typeof m !== "string" || m === "then") return undefined;
        return function (o) { return C.nativePromise(n, m, o || {}); };
      } });
    });
  } catch (e) {}
})();
</script>
"""
h = HTML.read_text(encoding="utf-8")
if "__plugin_fallback__" not in h:
    anchor = '<meta charset="utf-8">'
    if anchor in h:
        h = h.replace(anchor, anchor + "\n" + FALLBACK, 1)
    elif "<head>" in h:
        h = h.replace("<head>", "<head>\n" + FALLBACK, 1)
    else:
        sys.exit("no <head> anchor")
    HTML.write_text(h, encoding="utf-8")
print("html fallback added")
