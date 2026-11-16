// Datos de prueba basados en los ejemplos de contracts/. Solo se usan con VITE_USE_MOCK=true.

const ahora = () => new Date().toISOString().replace(/\.\d{3}Z$/, 'Z')

const USUARIOS = {
  tecnico: { rol: 'tecnico', nombre: 'Rosa Quispe' },
  supervisor: { rol: 'supervisor', nombre: 'Carlos Huamán' },
  gerente: { rol: 'gerente', nombre: 'Lucía Torres' },
}

const maquinas = [
  { maquina_id: 'EXC-007', modelo: 'EXC-320', zona: 'TAJO_NORTE', lat: -15.840, lon: -70.020, estado: 'OPERANDO', horas_motor: 4521.5, ultima_lectura: '2026-11-15T15:00:00Z', riesgo: 'MEDIO' },
  { maquina_id: 'EXC-008', modelo: 'EXC-320', zona: 'TAJO_NORTE', lat: -15.843, lon: -70.015, estado: 'OPERANDO', horas_motor: 3980.0, ultima_lectura: '2026-11-15T15:00:00Z', riesgo: 'BAJO' },
  { maquina_id: 'CAM-012', modelo: 'CAM-793', zona: 'RAMPA_ESTE', lat: -15.852, lon: -70.004, estado: 'OPERANDO', horas_motor: 6120.2, ultima_lectura: '2026-11-15T14:58:00Z', riesgo: 'BAJO' },
  { maquina_id: 'CAM-013', modelo: 'CAM-793', zona: 'RAMPA_ESTE', lat: -15.855, lon: -70.009, estado: 'DETENIDA', horas_motor: 7011.0, ultima_lectura: '2026-11-15T14:40:00Z', riesgo: 'ALTO' },
  { maquina_id: 'CAR-003', modelo: 'CAR-980', zona: 'BOTADERO_SUR', lat: -15.866, lon: -70.030, estado: 'RALENTI', horas_motor: 2210.4, ultima_lectura: '2026-11-15T14:59:00Z', riesgo: 'BAJO' },
  { maquina_id: 'PER-001', modelo: 'PER-D65', zona: 'TALLER_CENTRAL', lat: -15.835, lon: -70.035, estado: 'MANTENIMIENTO', horas_motor: 5402.9, ultima_lectura: '2026-11-15T12:00:00Z', riesgo: 'BAJO' },
]

const incidentes = [
  {
    tenant_id: 'MINA_SUR', incidente_id: '3f2c9a1e-7b44-4c1a-9a51-2d0e8f6b1c11',
    maquina_id: 'EXC-007', modelo: 'EXC-320', zona: 'TAJO_NORTE', lat: -15.84, lon: -70.02,
    creado_ts: '2026-11-15T15:05:00Z', estado: 'ASIGNADO', severidad: 'MEDIA',
    variables_anomalas: [
      { variable: 'temp_motor_c', valor: 104.3, media_habitual: 88.0, z: 3.1, minutos_persistente: 25 },
      { variable: 'vibracion_mm_s', valor: 7.9, media_habitual: 4.1, z: 2.8, minutos_persistente: 20 },
      { variable: 'combustible_l_h', valor: 46.0, media_habitual: 37.5, z: 2.6, minutos_persistente: 30 },
    ],
    analisis_ia: {
      nivel_riesgo: 'MEDIO',
      resumen: 'Temperatura, vibración y consumo suben juntos desde hace ~25 min respecto al historial de la máquina. Merece revisión; no hay evidencia suficiente para afirmar una causa.',
      posibles_causas_a_revisar: ['Sistema de enfriamiento', 'Montajes del motor', 'Filtro de aire'],
      especialidad_sugerida: 'MOTOR',
      mensajes_por_rol: {
        tecnico: 'EXC-007 (Tajo Norte): temp 104 °C (+3.1σ), vibración 7.9 mm/s (+2.8σ), consumo 46 L/h (+2.6σ) sostenidos 25 min. Revisar enfriamiento y montajes.',
        supervisor: 'EXC-007 con anomalía media. Asignada a Rosa Quispe (motor), llegada estimada 12 min.',
        gerente: 'Una excavadora de Tajo Norte en revisión preventiva. Sin detención por ahora.',
      },
      es_diagnostico: false, fuente: 'GEMINI',
    },
    grupo_causa_comun: null,
    tecnico_asignado: { tecnico_id: 'TEC-03', nombre: 'Rosa Quispe', especialidad: 'MOTOR', eta_min: 12, razon: 'Especialidad MOTOR coincide; disponible; 2.1 km (ETA 12 min); 0 incidentes activos. Descartado TEC-01 (ocupado).' },
    repuestos: [{ repuesto_id: 'FILTRO-AIRE-320', almacen: 'TALLER_CENTRAL', cantidad: 1, disponible: true }],
    linea_tiempo: [
      { ts: '2026-11-15T15:05:00Z', evento: 'DETECTADO', detalle: '3 variables desviadas' },
      { ts: '2026-11-15T15:05:04Z', evento: 'ANALIZADO', detalle: 'Riesgo MEDIO (Gemini)' },
      { ts: '2026-11-15T15:05:06Z', evento: 'ASIGNADO', detalle: 'TEC-03, ETA 12 min' },
    ],
    cierre: null,
  },
  {
    tenant_id: 'MINA_SUR', incidente_id: '9b1d6e20-1c5a-4f7e-8d2b-7a0c3e4f5a66',
    maquina_id: 'CAM-013', modelo: 'CAM-793', zona: 'RAMPA_ESTE', lat: -15.855, lon: -70.009,
    creado_ts: '2026-11-15T14:40:00Z', estado: 'EN_ATENCION', severidad: 'CRITICA',
    variables_anomalas: [
      { variable: 'presion_hid_bar', valor: 182, media_habitual: 305, z: -4.2, minutos_persistente: 15 },
      { variable: 'temp_motor_c', valor: 117.5, media_habitual: 90.1, z: 4.0, minutos_persistente: 12 },
      { variable: 'rpm', valor: 2350, media_habitual: 1820, z: 3.0, minutos_persistente: 10 },
    ],
    analisis_ia: {
      nivel_riesgo: 'ALTO',
      resumen: 'Caída de presión hidráulica con temperatura fuera de rango físico. Merece revisión inmediata; los datos no permiten confirmar la causa.',
      posibles_causas_a_revisar: ['Fuga en circuito hidráulico', 'Bomba hidráulica', 'Radiador'],
      especialidad_sugerida: 'HIDRAULICO',
      mensajes_por_rol: {
        tecnico: 'CAM-013 (Rampa Este): presión 182 bar (−4.2σ), temp 117.5 °C (fuera de rango). Revisar fugas y bomba hidráulica.',
        supervisor: 'CAM-013 detenida por anomalía crítica. Atiende Jorge Mamani (hidráulico), en sitio.',
        gerente: 'Un camión de Rampa Este está detenido por una revisión urgente.',
      },
      es_diagnostico: false, fuente: 'GEMINI',
    },
    grupo_causa_comun: 'GRP-RAMPA_ESTE-1440',
    tecnico_asignado: { tecnico_id: 'TEC-05', nombre: 'Jorge Mamani', especialidad: 'HIDRAULICO', eta_min: 8, razon: 'Especialidad HIDRAULICO coincide; disponible; 1.2 km (ETA 8 min).' },
    repuestos: [{ repuesto_id: 'BOMBA-HID-793', almacen: 'TALLER_CENTRAL', cantidad: 1, disponible: false }],
    linea_tiempo: [
      { ts: '2026-11-15T14:40:00Z', evento: 'DETECTADO', detalle: '3 variables desviadas, 1 fuera de rango' },
      { ts: '2026-11-15T14:40:05Z', evento: 'ANALIZADO', detalle: 'Riesgo ALTO (Gemini)' },
      { ts: '2026-11-15T14:40:07Z', evento: 'CAUSA_COMUN', detalle: '3 incidentes en RAMPA_ESTE en 60 min' },
      { ts: '2026-11-15T14:40:09Z', evento: 'ASIGNADO', detalle: 'TEC-05, ETA 8 min' },
      { ts: '2026-11-15T14:49:00Z', evento: 'EN_ATENCION', detalle: 'Técnico en sitio' },
    ],
    cierre: null,
  },
  {
    tenant_id: 'MINA_SUR', incidente_id: 'c4e7a9b2-55d1-4b0e-9e3f-1f2a3b4c5d77',
    maquina_id: 'CAM-012', modelo: 'CAM-793', zona: 'RAMPA_ESTE', lat: -15.852, lon: -70.004,
    creado_ts: '2026-11-15T14:20:00Z', estado: 'ANALIZADO', severidad: 'OBSERVACION',
    variables_anomalas: [
      { variable: 'combustible_l_h', valor: 61.0, media_habitual: 52.0, z: 2.6, minutos_persistente: 40 },
    ],
    analisis_ia: {
      nivel_riesgo: 'BAJO',
      resumen: 'Consumo de combustible por encima de su historial. Puede depender de la carga o del terreno; conviene observar.',
      posibles_causas_a_revisar: ['Carga transportada', 'Filtro de combustible'],
      especialidad_sugerida: 'GENERAL',
      mensajes_por_rol: {
        tecnico: 'CAM-012: consumo 61 L/h (+2.6σ) por 40 min. Observar; revisar filtro si persiste.',
        supervisor: 'CAM-012 en observación por consumo alto. Sin asignación por ahora.',
        gerente: 'Un camión con consumo algo elevado, en observación.',
      },
      es_diagnostico: false, fuente: 'PLANTILLA',
    },
    grupo_causa_comun: 'GRP-RAMPA_ESTE-1440',
    tecnico_asignado: null, repuestos: [],
    linea_tiempo: [
      { ts: '2026-11-15T14:20:00Z', evento: 'DETECTADO', detalle: '1 variable desviada' },
      { ts: '2026-11-15T14:20:03Z', evento: 'ANALIZADO', detalle: 'Observación (plantilla)' },
    ],
    cierre: null,
  },
]

const tecnicos = [
  { tecnico_id: 'TEC-01', nombre: 'Miguel Ccori', especialidad: 'MOTOR', zona: 'TAJO_NORTE', disponible: false, incidentes_activos: 1 },
  { tecnico_id: 'TEC-03', nombre: 'Rosa Quispe', especialidad: 'MOTOR', zona: 'TAJO_NORTE', disponible: false, incidentes_activos: 1 },
  { tecnico_id: 'TEC-05', nombre: 'Jorge Mamani', especialidad: 'HIDRAULICO', zona: 'RAMPA_ESTE', disponible: false, incidentes_activos: 1 },
  { tecnico_id: 'TEC-07', nombre: 'Ana Flores', especialidad: 'ELECTRICO', zona: 'TALLER_CENTRAL', disponible: true, incidentes_activos: 0 },
]

const reporte = {
  tenant_id: 'MINA_SUR', fecha: '2026-11-15',
  resumen_gerente: 'La flota opera con normalidad en general. Hay una excavadora en Tajo Norte en revisión preventiva y un camión detenido en Rampa Este por una revisión urgente; en esa zona se agrupan varios avisos, lo que merece investigar una posible causa común. Un camión consume más combustible que los de su mismo modelo. Una cargadora pasa la mayor parte del día sin uso. El filtro de aire del modelo EXC-320 podría faltar esta semana.',
  prioridades: ['Asegurar la bomba hidráulica para CAM-013', 'Programar mantenimiento preventivo de EXC-007', 'Reasignar o reubicar la cargadora CAR-003'],
  preventivo: [
    { maquina_id: 'EXC-007', horas_desde_mant: 520, carga_media_t: 27.5, prioridad: 'ALTA' },
    { maquina_id: 'CAM-012', horas_desde_mant: 410, carga_media_t: 180.0, prioridad: 'MEDIA' },
  ],
  combustible: [{ maquina_id: 'CAM-012', modelo: 'CAM-793', l_por_t: 0.34, mediana_modelo: 0.25, exceso_pct: 36 }],
  utilizacion: [
    { maquina_id: 'CAR-003', pct_operando: 18, horas_dia: 4.3, costo_dia_usd: 640, tipo: 'OCIOSA' },
    { maquina_id: 'CAM-013', pct_operando: 92, horas_dia: 22.1, costo_dia_usd: 1890, tipo: 'SOBREUSADA' },
  ],
  repuestos: [{ repuesto_id: 'FILTRO-AIRE-320', stock: 2, demanda_7d: 5, stock_minimo: 3 }],
}

const espera = (ms) => new Promise((r) => setTimeout(r, ms))
const copia = (x) => JSON.parse(JSON.stringify(x))

export async function mockApi(ruta, { method = 'GET', body } = {}) {
  await espera(250)
  const [camino, query] = ruta.split('?')
  const partes = camino.split('/').filter(Boolean)

  if (method === 'POST' && camino === '/login') {
    const u = USUARIOS[body?.usuario]
    if (!u || body?.password !== 'demo123') throw new Error('Usuario o contraseña incorrectos (demo: tecnico / supervisor / gerente, clave demo123)')
    return { token: 'mock-token', rol: u.rol, tenant_id: 'MINA_SUR', nombre: u.nombre }
  }
  if (camino === '/maquinas') return copia(maquinas)
  if (partes[0] === 'maquinas' && partes[1]) {
    const m = maquinas.find((x) => x.maquina_id === partes[1])
    return { ...copia(m), lecturas: [], incidentes: copia(incidentes.filter((i) => i.maquina_id === partes[1])) }
  }
  if (camino === '/incidentes') {
    const abiertos = query?.includes('ABIERTOS')
    return copia(incidentes.filter((i) => !abiertos || !['CERRADO', 'DESCARTADO'].includes(i.estado)))
  }
  if (partes[0] === 'incidentes' && partes[1] && partes[2] === 'cerrar' && method === 'POST') {
    const i = incidentes.find((x) => x.incidente_id === partes[1])
    i.estado = 'CERRADO'
    i.cierre = { cerrado_ts: ahora(), ...body }
    i.linea_tiempo.push({ ts: ahora(), evento: 'CERRADO', detalle: body.intervencion })
    return { ok: true }
  }
  if (partes[0] === 'incidentes' && partes[1]) return copia(incidentes.find((x) => x.incidente_id === partes[1]))
  if (camino === '/tecnicos') return copia(tecnicos)
  if (camino === '/reportes/ultimo') return copia(reporte)
  throw new Error(`Ruta de prueba no definida: ${ruta}`)
}
