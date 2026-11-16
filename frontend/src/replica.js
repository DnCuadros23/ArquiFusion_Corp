// Lectura de la réplica en Firestore (solo se carga en modo degradado).
import { initializeApp } from 'firebase/app'
import { getFirestore, collection, getDocs } from 'firebase/firestore'

let db = null

function conectar() {
  if (!db) {
    const config = {
      apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
      authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
      projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
      appId: import.meta.env.VITE_FIREBASE_APP_ID,
    }
    if (!config.projectId) throw new Error('La API no responde y Firebase no está configurado')
    db = getFirestore(initializeApp(config))
  }
  return db
}

export async function leerColeccion(nombre) {
  const instantanea = await getDocs(collection(conectar(), nombre))
  return instantanea.docs.map((d) => d.data())
}
