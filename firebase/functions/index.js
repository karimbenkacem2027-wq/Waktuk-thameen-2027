const { onCall, HttpsError } = require('firebase-functions/v2/https');
const { defineSecret } = require('firebase-functions/params');
const { initializeApp } = require('firebase-admin/app');
const { getFirestore, FieldValue, Timestamp } = require('firebase-admin/firestore');

initializeApp();
const db = getFirestore();
const OPENAI_API_KEY = defineSecret('OPENAI_API_KEY');

// Stores only a daily request counter. User questions and usage details are not persisted.
exports.waqtakAIAdvisor = onCall({ secrets: [OPENAI_API_KEY], timeoutSeconds: 45, memory: '256MiB' }, async (request) => {
  if (!request.auth) throw new HttpsError('unauthenticated', 'Sign in anonymously before using the assistant.');
  const uid = request.auth.uid;
  const question = String(request.data?.question || '').trim().slice(0, 1200);
  const snapshot = request.data?.snapshot || {};
  if (!question) throw new HttpsError('invalid-argument', 'Write a question first.');

  const counterRef = db.collection('ai_usage').doc(uid);
  const dayKey = new Date().toISOString().slice(0, 10);
  const allowed = await db.runTransaction(async (tx) => {
    const snap = await tx.get(counterRef);
    const data = snap.exists ? snap.data() : {};
    const count = data.day === dayKey ? Number(data.count || 0) : 0;
    if (count >= 20) return false;
    tx.set(counterRef, { day: dayKey, count: count + 1, updatedAt: FieldValue.serverTimestamp() }, { merge: true });
    return true;
  });
  if (!allowed) throw new HttpsError('resource-exhausted', 'Daily AI limit reached. Try again tomorrow.');

  const usage = Math.max(0, Math.min(Number(snapshot.usageTodaySeconds || 0), 86400));
  const apps = Array.isArray(snapshot.topApps) ? snapshot.topApps.slice(0, 5).map(x => ({
    name: String(x.name || 'Unknown app').slice(0, 60),
    seconds: Math.max(0, Math.min(Number(x.seconds || 0), 86400))
  })) : [];
  const focusMinutes = Math.max(0, Math.min(Number(snapshot.focusMinutes30d || 0), 100000));

  const payload = {
    model: 'gpt-4o-mini',
    messages: [
      { role: 'system', content: 'You are Waqtak, a concise productivity coach. Answer in the user\'s language. Give practical, non-judgmental advice based only on supplied metrics. Never invent measurements, diagnose addiction or medical conditions, or present worship as a score. If data is missing, say so.' },
      { role: 'user', content: JSON.stringify({ question, metrics: { usageTodaySeconds: usage, topApps: apps, focusMinutes30d: focusMinutes } }) }
    ],
    temperature: 0.4,
    max_tokens: 500
  };
  const response = await fetch('https://api.openai.com/v1/chat/completions', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${OPENAI_API_KEY.value()}`, 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    console.error('AI provider returned status', response.status);
    throw new HttpsError('unavailable', 'The AI service is temporarily unavailable.');
  }
  const result = await response.json();
  const answer = String(result.choices?.[0]?.message?.content || '').trim();
  if (!answer) throw new HttpsError('internal', 'The AI service returned an empty answer.');
  return { answer };
});
