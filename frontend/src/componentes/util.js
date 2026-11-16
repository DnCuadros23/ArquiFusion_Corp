export const COLOR_ESTADO = {
  OPERANDO: '#1f9d55',
  RALENTI: '#7a8a99',
  DETENIDA: '#c0392b',
  MANTENIMIENTO: '#2e6fd8',
  RIESGO: '#e67e22',
}

// "En riesgo" tiene prioridad sobre el estado operativo para el color del mapa
export function colorMaquina(m) {
  if (m.estado === 'DETENIDA') return COLOR_ESTADO.DETENIDA
  if (m.riesgo === 'ALTO' || m.riesgo === 'MEDIO') return COLOR_ESTADO.RIESGO
  return COLOR_ESTADO[m.estado] || COLOR_ESTADO.RALENTI
}

export const NOMBRE_VARIABLE = {
  temp_motor_c: 'Temperatura motor (°C)',
  vibracion_mm_s: 'Vibración (mm/s)',
  presion_hid_bar: 'Presión hidráulica (bar)',
  combustible_l_h: 'Combustible (L/h)',
  carga_t: 'Carga (t)',
  velocidad_kmh: 'Velocidad (km/h)',
  rpm: 'RPM',
}

export function fecha(ts) {
  if (ts && typeof ts === 'object') ts = ts.ts || ts.timestamp || ts.fecha || ts.ts_iso
  if (!ts) return '—'
  if (typeof ts === 'number' && ts < 1e12) ts *= 1000   // epoch en segundos
  const d = new Date(ts)
  return isNaN(d) ? ts : d.toLocaleString('es-PE', { dateStyle: 'short', timeStyle: 'short' })
}

// Convierte cualquier valor en texto seguro para React (un objeto nunca debe renderizarse directo)
export function texto(v) {
  if (v === null || v === undefined || v === '') return '—'
  if (typeof v === 'number') return Number.isInteger(v) ? String(v) : v.toFixed(1)
  if (typeof v === 'object') return JSON.stringify(v)
  return String(v)
}

export const numero = (v, dec = 1) => {
  const n = typeof v === 'string' && v.trim() !== '' && !isNaN(v) ? Number(v) : v
  return typeof n === 'number' ? n.toFixed(dec) : texto(v)
}
