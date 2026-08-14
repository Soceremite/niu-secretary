
// fitness/src/js/lib/db.js
const DB_NAME = 'NiuyeyeFitnessDB';
const DB_VERSION = 4;
const STORES = ['profile', 'weightLogs', 'assessmentLogs', 'nutritionLogs', 'trainingLogs', 'recoveryLogs', 'consultLogs', 'syncQueue'];
const SYNCED_STORES = ['weightLogs', 'assessmentLogs', 'nutritionLogs', 'trainingLogs', 'recoveryLogs', 'consultLogs'];

let dbPromise;

export function getDb() {
  if (!dbPromise) {
    dbPromise = new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);
      request.onupgradeneeded = () => {
        const db = request.result;
        for (const name of STORES) {
          if (!db.objectStoreNames.contains(name)) {
            const options = name === 'profile' ? { keyPath: 'key' } : { keyPath: 'id', autoIncrement: true };
            const store = db.createObjectStore(name, options);
            if (name !== 'profile' && name !== 'syncQueue') store.createIndex('date', 'date', { unique: false });
            if (name === 'syncQueue') store.createIndex('status', 'status', { unique: false });
          }
        }
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }
  return dbPromise;
}

export async function putProfile(value) {
  const db = await getDb();
  return tx(db, 'profile', 'readwrite', (store) => store.put({ key: 'main', value, updatedAt: nowIso() }));
}

export async function getProfile() {
  const db = await getDb();
  const row = await tx(db, 'profile', 'readonly', (store) => store.get('main'));
  return row?.value || null;
}

export async function addWeightLog(log) { return addSynced('weightLogs', 'weightLog', log); }
export async function listWeightLogs() { return listRows('weightLogs'); }
export async function clearWeightLogs() { return clearStore('weightLogs'); }
export async function addAssessmentLog(log) { return addSynced('assessmentLogs', 'assessmentLog', log); }
export async function listAssessmentLogs() { return listRows('assessmentLogs'); }
export async function addTrainingLog(log) { return addSynced('trainingLogs', 'trainingLog', log); }
export async function listTrainingLogs() { return listRows('trainingLogs'); }
export async function clearTrainingLogs() { return clearStore('trainingLogs'); }
export async function addNutritionLog(log) { return addSynced('nutritionLogs', 'nutritionLog', log); }
export async function listNutritionLogs() { return listRows('nutritionLogs'); }
export async function clearNutritionLogs() { return clearStore('nutritionLogs'); }
export async function addRecoveryLog(log) { return addSynced('recoveryLogs', 'recoveryLog', log); }
export async function listRecoveryLogs() { return listRows('recoveryLogs'); }
export async function clearRecoveryLogs() { return clearStore('recoveryLogs'); }
export async function addConsultLog(log) { return addSynced('consultLogs', 'consultLog', log); }
export async function listConsultLogs() { return listRows('consultLogs'); }

export async function enqueueSync(type, payload) {
  const db = await getDb();
  return tx(db, 'syncQueue', 'readwrite', (store) => store.add({
    type,
    payload,
    status: 'pending',
    retryCount: 0,
    createdAt: nowIso(),
    updatedAt: nowIso()
  }));
}

export async function countRealPending() {
  const db = await getDb();
  let count = 0;
  for (const storeName of SYNCED_STORES) {
    const rows = await tx(db, storeName, 'readonly', (store) => store.getAll());
    count += rows.filter((row) => row.syncStatus === 'pending').length;
  }
  return count;
}

export async function exportAllData() {
  const db = await getDb();
  const data = { exportedAt: nowIso(), version: DB_VERSION, stores: {} };
  for (const storeName of STORES) {
    data.stores[storeName] = await tx(db, storeName, 'readonly', (store) => store.getAll());
  }
  return data;
}


async function addSynced(storeName, type, row) {
  const normalized = normalizeRecord(row);
  const id = await addRow(storeName, normalized);
  await enqueueSync(type, { ...normalized, id });
  return id;
}

async function addRow(storeName, row) {
  const db = await getDb();
  return tx(db, storeName, 'readwrite', (store) => store.add(row));
}

async function listRows(storeName) {
  const db = await getDb();
  const rows = await tx(db, storeName, 'readonly', (store) => store.getAll());
  return rows.map((row) => SYNCED_STORES.includes(storeName) ? normalizeRecord(row) : row);
}

async function clearStore(storeName) {
  const db = await getDb();
  return tx(db, storeName, 'readwrite', (store) => store.clear());
}

function normalizeRecord(row) {
  const createdAt = row.createdAt || nowIso();
  return {
    ...row,
    createdAt,
    updatedAt: row.updatedAt || createdAt,
    source: row.source || 'manual',
    syncStatus: row.syncStatus || 'pending'
  };
}

function nowIso() {
  return new Date().toISOString();
}

function tx(db, storeName, mode, action) {
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(storeName, mode);
    const store = transaction.objectStore(storeName);
    const request = action(store);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
    transaction.onerror = () => reject(transaction.error);
  });
}
