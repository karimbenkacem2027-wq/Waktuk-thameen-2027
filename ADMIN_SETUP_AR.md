# إعداد لوحة إدارة «وقتك ثمين»

## ما الذي أُضيف؟
- مدخل لوحة الإدارة داخل صفحة الإعدادات.
- تسجيل دخول Firebase بالبريد وكلمة المرور.
- فحص صلاحية `role=admin` و`active=true` من وثيقة `users/{uid}`.
- إنشاء/عرض/حذف المنشورات والآيات والأحاديث والتذكيرات والإعلانات في Firestore.
- بطاقات إحصاءات جاهزة، وتعرض — حتى ربط نظام القياس — شرطة بدل أرقام وهمية.
- قواعد Firestore تمنع المستخدم العادي من تعديل المحتوى أو الإحصاءات.

## خطوات الربط المطلوبة
1. أنشئ مشروعاً في https://console.firebase.google.com
2. أضف تطبيق Web إلى مشروع Firebase وانسخ إعدادات Firebase إلى `admin/firebase-config.js`.
3. من Authentication فعّل Email/Password وأنشئ حسابك كمدير.
4. من Firestore أنشئ قاعدة بيانات، ثم انشر ملف `firestore.rules`.
5. انسخ UID لحسابك من Authentication، وأنشئ وثيقة `users/{UID}` بهذه البيانات:
   - `role`: `admin`
   - `active`: `true`
6. أعد بناء التطبيق بعد حفظ إعدادات Firebase.

## مهم قبل الإطلاق
- لوحة الإدارة لا تعمل فعلياً حتى تُدخل إعدادات Firebase وتُنشئ حساب المدير وتطبق القواعد.
- عدادات التثبيت/التحميل والنشطين ليست أرقاماً جاهزة بعد. يجب إضافة تسجيل أول تشغيل وقياس الجلسات، وتحديث الأرقام عبر Cloud Functions آمنة. تحميل APK يقاس من رابط التنزيل أو منصة التوزيع، وليس من Firebase Analytics وحده.
- إرسال الإشعارات الجماعية يحتاج Firebase Cloud Messaging مع خادم موثوق/Cloud Function. لا ترسل مفاتيح الخادم من التطبيق.
- لا تضع كلمة مرور المدير أو Service Account داخل ملفات التطبيق أو GitHub.


## تشغيل مساعد الذكاء الاصطناعي في V3

1. من Firebase Authentication فعّل مزود Anonymous.
2. ثبّت Firebase CLI وسجّل الدخول: `npm install -g firebase-tools` ثم `firebase login`.
3. اربط مجلد المشروع بمشروع Firebase: `firebase use --add`.
4. أضف مفتاح مزود الذكاء الاصطناعي إلى Secret Manager: `firebase functions:secrets:set OPENAI_API_KEY`.
5. ثبّت اعتماديات الوظيفة: `cd firebase/functions && npm install` ثم ارجع إلى جذر المشروع.
6. انشر الوظيفة: `firebase deploy --only functions:waqtakAIAdvisor`.

لا تضع مفتاح API في `www/` أو `admin/` أو أي ملف يصل إلى المستخدم. الوظيفة لا تحفظ نص السؤال أو إجابة المساعد، لكنها تحفظ عداد الاستخدام اليومي لكل UID في مجموعة `ai_usage`.
