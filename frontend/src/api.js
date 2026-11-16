import { mockApi } from './mock.js'

const API_URL = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')
export const USA_MOCK = import.meta.env.VITE_USE_MOCK === 'true' || !API_URL
const TIEMPO_MAXIMO_MS = 5000

// ---------- Sesión (sessionStorage: se borra al cerrar la pestaña) ----------

export function leerSesion() {
  try {
    return JSON.parse(sessionStorage.getItem('sesion')) || null
  } catch {
    return null
  }
}

export function guardarSesion(sesion) {
  try {
    if (sesion) sessionStorage.setItem('sesion', JSON.stringify(sesion))
    else sessionStorage.removeItem('sesion')
  } catch {
    /* sin almacenamiento: la sesión vive solo en memoria */
  }
}

// ---------- Modo degradado ----------

let degradado = false
const oyentes = new Set()

export function enModoDegradado() {
  return degradado
}

export function alCambiarModo(fn) {
  oyentes.add(fn)
  return () => oyentes.delete(fn)
}

function cambiarModo(valor) {
  if (degradado !== valor) {
    degradado = valor
    oyentes.forEach((fn) => fn(valor))
  }
}

// ---------- Llamadas ----------

class ErrorApi extends Error {
  constructor(mensaje, estado) {
    super(mensaje)
    this.estado = estado
  }
}

async function llamar(ruta, { method = 'GET', body } = {}) {
  if (USA_MOCK) return mockApi(ruta, { method, body })

  const sesion = leerSesion()
  const controlador = new AbortController()
  const reloj = setTimeout(() => controlador.abort(), TIEMPO_MAXIMO_MS)
  try {
    const respuesta = await fetch(`${API_URL}${ruta}`, {
      method,
      signal: controlador.signal,
      headers: {
        'Content-Type': 'application/json',
        ...(sesion?.token ? { Authorization: `Bearer ${sesion.token}` } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
    })
    const datos = await respuesta.json().catch(() => ({}))
    if (!respuesta.ok) throw new ErrorApi(datos.mensaje || datos.message || datos.error || `Error ${respuesta.status}`, respuesta.status)
    cambiarModo(false)
    return datos
  } catch (e) {
    if (e instanceof ErrorApi) throw e
    throw new ErrorApi('La API no responde', 0)   // timeout o red caída
  } finally {
    clearTimeout(reloj)
  }
}

// Lecturas con respaldo: si la API no responde, se lee la réplica de Firestore.
async function leerConRespaldo(ruta, coleccion) {
  try {
    return await llamar(ruta)
  } catch (e) {
    if (e.estado !== 0 || USA_MOCK) throw e
    const { leerColeccion } = await import('./replica.js')
    const datos = await leerColeccion(coleccion)
    cambiarModo(true)
    return datos
  }
}

// ---------- Normalización (tolera pequeñas variaciones del formato de la API) ----------

function leerJwt(token) {
  try {
    const base = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')
    return JSON.parse(decodeURIComponent(escape(atob(base))))
  } catch {
    return {}
  }
}

function normalizarRol(rol) {
  const r = String(rol || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '')
  if (r.startsWith('tecnico')) return 'tecnico'
  if (r.startsWith('super')) return 'supervisor'
  if (r.startsWith('geren')) return 'gerente'
  return r
}

function normalizarSesion(r, usuario) {
  const d = r?.data || r || {}
  const u = d.usuario && typeof d.usuario === 'object' ? d.usuario : d.user || {}
  const token = d.token || d.access_token || d.jwt
  if (!token) throw new ErrorApi('La API no devolvió token', 500)
  const jwt = leerJwt(token)
  return {
    token,
    rol: normalizarRol(d.rol || d.role || u.rol || u.role || jwt.rol || jwt.role),
    tenant_id: d.tenant_id || u.tenant_id || jwt.tenant_id || '',
    nombre: d.nombre || u.nombre || jwt.nombre || jwt.name || (typeof d.usuario === 'string' ? d.usuario : '') || jwt.sub || usuario,
  }
}

function lista(r) {
  if (Array.isArray(r)) return r
  for (const k of ['items', 'datos', 'data', 'maquinas', 'incidentes', 'tecnicos', 'Items']) if (Array.isArray(r?.[k])) return r[k]
  return []
}

export const api = {
  login: async (usuario, password) => normalizarSesion(await llamar('/login', { method: 'POST', body: { usuario, password } }), usuario),
  maquinas: async () => lista(await leerConRespaldo('/maquinas', 'maquinas')),
  incidentes: async (soloAbiertos) =>
    lista(await leerConRespaldo(soloAbiertos ? '/incidentes?estado=ABIERTOS' : '/incidentes', 'incidentes')),
  incidente: async (id) => { const r = await llamar(`/incidentes/${encodeURIComponent(id)}`); return r?.incidente || r?.data || r },
  cerrarIncidente: (id, datos) => llamar(`/incidentes/${encodeURIComponent(id)}/cerrar`, { method: 'POST', body: datos }),
  tecnicos: async () => lista(await llamar('/tecnicos')),
  reporte: async () => { const r = await llamar('/reportes/ultimo'); return r?.reporte || r?.data || r },
}
