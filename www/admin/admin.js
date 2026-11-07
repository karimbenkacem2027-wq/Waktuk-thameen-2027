
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.14.1/firebase-app.js";

import {
  getAuth,
  signInWithEmailAndPassword,
  signOut,
  onAuthStateChanged
} from "https://www.gstatic.com/firebasejs/10.14.1/firebase-auth.js";

import {
  getFirestore,
  doc,
  getDoc,
  collection,
  addDoc,
  getDocs,
  deleteDoc,
  query,
  orderBy,
  serverTimestamp
} from "https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js";

import { firebaseConfig } from "./firebase-config.js";

const root = document.getElementById("admin-root");

const configured =
  firebaseConfig.apiKey !== "YOUR_FIREBASE_API_KEY" &&
  firebaseConfig.projectId !== "YOUR_PROJECT_ID";

let auth, db, currentUser;

const esc = s =>
  String(s ?? "").replace(/[&<>"']/g, c => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  }[c]));

const shell = html => {
  root.innerHTML = `
    <section class="wa-admin">
      <div class="wa-admin-card">
        <button class="wa-close" id="wa-close">✕</button>
        ${html}
      </div>
    </section>
  `;

  document.getElementById("wa-close").onclick = closeAdmin;
};

const style = document.createElement("style");

style.textContent = `
.wa-admin {
  position: fixed;
  inset: 0;
  z-index: 99999;
  background: #061b17ed;
  overflow: auto;
  padding: 18px;
  display: grid;
  place-items: center;
  font-family: system-ui;
}
.wa-admin-card {
  position: relative;
  background: #102a23;
  color: #f5f3e9;
  border: 1px solid #b99b55;
  border-radius: 20px;
  padding: 22px;
  width: min(100%,560px);
  max-height: 94vh;
  overflow: auto;
  direction: rtl;
}
.wa-admin h2 { color: #e4c77b; }
.wa-admin input,
.wa-admin textarea,
.wa-admin select {
  box-sizing: border-box;
  width: 100%;
  padding: 12px;
  margin: 7px 0;
  border-radius: 10px;
  border: 1px solid #557268;
  background: #091d18;
  color: white;
}
.wa-admin button {
  padding: 11px 15px;
  border: 0;
  border-radius: 10px;
  background: #c7a65b;
  color: #10251f;
  font-weight: 700;
  margin: 5px;
  cursor: pointer;
}
.wa-admin .wa-close {
  float: left;
  background: #263f37;
  color: white;
}
.wa-admin .wa-muted {
  color: #b8c8c0;
  font-size: 13px;
}
.wa-admin .wa-stat {
  display: inline-block;
  background: #1c3c31;
  padding: 12px;
  border-radius: 12px;
  margin: 4px;
  min-width: 110px;
}
.wa-admin .wa-post {
  border: 1px solid #47685b;
  padding: 12px;
  border-radius: 12px;
  margin: 9px 0;
}
.wa-admin .wa-danger {
  background: #8e3b35;
  color: white;
}
`;

document.head.appendChild(style);

function closeAdmin() {
  root.innerHTML = "";
}

function loginView(msg = "") {
  shell(`
    <h2>🔐 دخول المدير</h2>
    <p class="wa-muted">
      هذه المنطقة مخصصة لحساب المدير المصرّح به فقط.
    </p>
    ${msg ? `<p>${esc(msg)}</p>` : ""}
    <form id="wa-login">
      <input id="wa-email" type="email"
        placeholder="البريد الإلكتروني" required>
      <input id="wa-pass" type="password"
        placeholder="كلمة المرور" required>
      <button>تسجيل الدخول</button>
    </form>
  `);

  document.getElementById("wa-login").onsubmit = async e => {
    e.preventDefault();

    try {
      await signInWithEmailAndPassword(
        auth,
        document.getElementById("wa-email").value,
        document.getElementById("wa-pass").value
      );
    } catch (err) {
      loginView(
        "تعذر تسجيل الدخول: " +
        err.code + " | " + err.message
      );
    }
  };
}

// فحص صلاحية المدير مع إظهار سبب المشكلة الحقيقي
async function isAdmin(user) {
  try {
    const snap = await getDoc(
      doc(db, "users", user.uid)
    );

    if (!snap.exists()) {
      alert(
        "لم يتم العثور على وثيقة المدير في Firestore.\n" +
        "UID: " + user.uid
      );
      return false;
    }

    const data = snap.data();

    if (data.role !== "admin") {
      alert(
        "قيمة role غير صحيحة.\n" +
        "القيمة الموجودة: " + data.role
      );
      return false;
    }

    if (data.active === false) {
      alert("حساب المدير غير نشط.");
      return false;
    }

    return true;

  } catch (error) {
    console.error("Admin permission error:", error);

    alert(
      "خطأ في قراءة صلاحية المدير:\n" +
      error.code + "\n" +
      error.message
    );

    return false;
  }
}

async function dashboard() {
  if (!await isAdmin(currentUser)) {
    await signOut(auth);
    loginView("تعذر التحقق من صلاحية المدير. راجع رسالة الخطأ.");
    return;
  }

  try {
    const [metricSnap, postsSnap] = await Promise.all([
      getDoc(doc(db, "metrics", "summary")),
      getDocs(
        query(
          collection(db, "posts"),
          orderBy("createdAt", "desc")
        )
      )
    ]);

    const m = metricSnap.exists()
      ? metricSnap.data()
      : {};

    const posts = postsSnap.docs.map(d => ({
      id: d.id,
      ...d.data()
    }));

    shell(`
      <h2>🛡️ لوحة إدارة وقتك ثمين</h2>

      <p class="wa-muted">
        مرحباً بك، ${esc(currentUser.email)}
      </p>

      <div>
        <span class="wa-stat">
          👥 المستخدمون<br>
          <b>${m.installs ?? "—"}</b>
        </span>

        <span class="wa-stat">
          🟢 النشطون<br>
          <b>${m.activeUsers ?? "—"}</b>
        </span>

        <span class="wa-stat">
          ⬇️ التحميلات<br>
          <b>${m.downloads ?? "—"}</b>
        </span>

        <span class="wa-stat">
          📝 المنشورات<br>
          <b>${posts.length}</b>
        </span>
      </div>

      <hr>

      <h3>نشر محتوى جديد</h3>

      <form id="wa-publish">
        <input id="wa-title"
          placeholder="عنوان المنشور" required>

        <select id="wa-type">
          <option value="post">منشور</option>
          <option value="ayah">آية قرآنية</option>
          <option value="hadith">حديث</option>
          <option value="reminder">تذكير</option>
          <option value="announcement">إعلان</option>
        </select>

        <textarea id="wa-body" rows="5"
          placeholder="اكتب المحتوى هنا" required></textarea>

        <label>
          <input id="wa-notify" type="checkbox"
            style="width:auto">
          طلب إرسال إشعار للمستخدمين
          (يتطلب إعداد Cloud Function)
        </label>

        <button>نشر الآن</button>
      </form>

      <h3>المحتوى المنشور</h3>

      <div id="wa-posts">
        ${
          posts.map(p => `
            <article class="wa-post">
              <b>${esc(p.title)}</b>
              <p>${esc(p.body)}</p>
              <small>${esc(p.type || "post")}</small>
              <button class="wa-danger"
                data-delete="${esc(p.id)}">
                حذف
              </button>
            </article>
          `).join("") ||
          '<p class="wa-muted">لا توجد منشورات بعد.</p>'
        }
      </div>

      <button id="wa-logout">تسجيل الخروج</button>

      <p class="wa-muted">
        الأرقام تظهر بعد تفعيل التسجيل التحليلي.
        الشرطة (—) تعني أن القياس لم يُربط بعد.
      </p>
    `);

    document.getElementById("wa-publish").onsubmit =
      async e => {
        e.preventDefault();

        const title =
          document.getElementById("wa-title").value.trim();

        const body =
          document.getElementById("wa-body").value.trim();

        const type =
          document.getElementById("wa-type").value;

        const notify =
          document.getElementById("wa-notify").checked;

        try {
          await addDoc(collection(db, "posts"), {
            title,
            body,
            type,
            notifyRequested: notify,
            published: true,
            createdAt: serverTimestamp(),
            createdBy: currentUser.uid
          });

          await dashboard();

        } catch (err) {
          alert("فشل النشر: " + err.message);
        }
      };

    document.querySelectorAll("[data-delete]")
      .forEach(b => {
        b.onclick = async () => {
          if (confirm("حذف هذا المنشور؟")) {
            try {
              await deleteDoc(
                doc(db, "posts", b.dataset.delete)
              );
              await dashboard();
            } catch (err) {
              alert("فشل الحذف: " + err.message);
            }
          }
        };
      });

    document.getElementById("wa-logout").onclick =
      () => signOut(auth);

  } catch (error) {
    console.error("Dashboard error:", error);

    shell(`
      <h2>تعذر تحميل لوحة الإدارة</h2>
      <p>${esc(error.code || "")}</p>
      <p>${esc(error.message)}</p>
      <button id="wa-retry">إعادة المحاولة</button>
    `);

    document.getElementById("wa-retry").onclick =
      () => dashboard();
  }
}

window.openWaqtakAdmin = () => {
  if (!configured) {
    shell(`
      <h2>إعداد لوحة الإدارة</h2>
      <p>
        لم يتم ربط Firebase بعد.
        أضف بيانات مشروع Firebase إلى الملف
        <b>admin/firebase-config.js</b>
        ثم أعد بناء التطبيق.
      </p>
      <p class="wa-muted">
        لا يمكن تسجيل الدخول أو نشر المحتوى أو عرض
        إحصائيات حقيقية قبل إكمال إعداد Firebase
        وقواعد الأمان.
      </p>
    `);
    return;
  }

  loginView();
};

async function renderPublicFeed() {
  if (!db) return;

  try {
    const snap = await getDocs(
      query(
        collection(db, "posts"),
        orderBy("createdAt", "desc")
      )
    );

    const rows = snap.docs
      .map(d => d.data())
      .filter(p => p.published === true);

    if (!rows.length) return;

    const host = document.querySelector("#app main");
    if (!host) return;

    const old = document.getElementById("wa-public-feed");
    if (old) old.remove();

    const box = document.createElement("section");

    box.id = "wa-public-feed";
    box.dir = "auto";

    box.style.cssText =
      "margin:18px 0;padding:16px;border:1px solid var(--ln);" +
      "border-radius:16px;background:var(--card)";

    box.innerHTML =
      "<h2>📢 " +
      (document.documentElement.lang === "en"
        ? "Latest updates"
        : "آخر المستجدات") +
      "</h2>" +
      rows.slice(0, 5).map(p => `
        <article style="padding:10px 0;border-bottom:1px solid var(--ln)">
          <b>${esc(p.title)}</b>
          <p>${esc(p.body)}</p>
        </article>
      `).join("");

    host.appendChild(box);

  } catch (e) {
    console.info(
      "Public feed unavailable until Firebase is configured",
      e
    );
  }
}

if (configured) {
  const app = initializeApp(firebaseConfig);

  auth = getAuth(app);
  db = getFirestore(app);

  onAuthStateChanged(auth, async user => {
    currentUser = user;

    if (user && root.innerHTML) {
      await dashboard();
    }
  });

  const observer = new MutationObserver(() => {
    renderPublicFeed();
  });

  observer.observe(
    document.getElementById("app"),
    {
      childList: true,
      subtree: true
    }
  );

  renderPublicFeed();
}
