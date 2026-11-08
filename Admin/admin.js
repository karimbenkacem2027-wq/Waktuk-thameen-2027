async function isAdmin(user) {
  try {
    const userRef = doc(db, 'users', user.uid);
    const snap = await getDoc(userRef);

    if (!snap.exists()) {
      alert('لم يتم العثور على وثيقة المدير في المسار: users/' + user.uid);
      return false;
    }

    const data = snap.data();

    return data.role === 'admin' && data.active === true;

  } catch (error) {
    console.error('Admin verification error:', error);
    alert('خطأ في التحقق من صلاحيات المدير: ' + error.message);
    return false;
  }
}
