import { useMemo, useState } from 'react'
import { CircleMarker, MapContainer, TileLayer, Tooltip } from 'react-leaflet'
import { api } from '../api.js'
import { usarDatos } from './usarDatos.js'
import Cargando from './Cargando.jsx'
import { COLOR_ESTADO, NOMBRE_VARIABLE, colorMaquina, fecha, numero, texto } from './util.js'

const LEYENDA = [['Operando', 'OPERANDO'], ['En riesgo', 'RIESGO'], ['Detenida', 'DETENIDA'], ['Mantenimiento', 'MANTENIMIENTO'], ['Ralentí', 'RALENTI']]

export default function Flota() {
  const estado = usarDatos(() => api.maquinas())
  const [seleccion, setSeleccion] = useState(null)
  const maquinas = estado.datos || []

  const centro = useMemo(() => {
    const conUbicacion = maquinas.filter((m) => Number.isFinite(m.lat) && Number.isFinite(m.lon))
    if (!conUbicacion.length) return [-15.84, -70.02]
    const lat = conUbicacion.reduce((s, m) => s + m.lat, 0) / conUbicacion.length
    const lon = conUbicacion.reduce((s, m) => s + m.lon, 0) / conUbicacion.length
    return [lat, lon]
  }, [maquinas])

  const conteo = useMemo(() => {
    const c = {}
    maquinas.forEach((m) => { c[m.estado] = (c[m.estado] || 0) + 1 })
    return c
  }, [maquinas])

  const elegida = maquinas.find((m) => m.maquina_id === seleccion)
  // ultima_lectura puede venir como fecha o como el objeto de telemetría completo
  const lectura = elegida && typeof elegida.ultima_lectura === 'object' ? elegida.ultima_lectura : null
  const variables = lectura ? lectura.variables || lectura : null

  return (
    <Cargando estado={estado}>
      <div className="indicadores">
        <div className="indicador"><b>{maquinas.length}</b><span>máquinas</span></div>
        {['OPERANDO', 'RALENTI', 'DETENIDA', 'MANTENIMIENTO'].map((e) => (
          <div className="indicador" key={e}><b>{conteo[e] || 0}</b><span>{e.toLowerCase()}</span></div>
        ))}
        <div className="indicador"><b>{maquinas.filter((m) => m.riesgo === 'ALTO' || m.riesgo === 'MEDIO').length}</b><span>en riesgo</span></div>
      </div>

      <div className="flota">
        <div className="mapa">
          {/* key={centro} recentra el mapa cuando llegan los datos */}
          <MapContainer key={centro.join(',')} center={centro} zoom={14} style={{ height: '100%', width: '100%' }}>
            <TileLayer attribution="&copy; OpenStreetMap" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
            {maquinas.filter((m) => typeof m.lat === 'number').map((m) => (
              <CircleMarker
                key={m.maquina_id}
                center={[m.lat, m.lon]}
                radius={m.maquina_id === seleccion ? 13 : 9}
                pathOptions={{ color: '#222', weight: 1, fillColor: colorMaquina(m), fillOpacity: 0.9 }}
                eventHandlers={{ click: () => setSeleccion(m.maquina_id) }}
              >
                <Tooltip>{texto(m.maquina_id)} · {texto(m.estado)}</Tooltip>
              </CircleMarker>
            ))}
          </MapContainer>
          <div className="leyenda">
            {LEYENDA.map(([t, k]) => <span key={k}><i style={{ background: COLOR_ESTADO[k] }} />{t}</span>)}
          </div>
        </div>

        <aside className="panel">
          {elegida ? (
            <>
              <h2>{elegida.maquina_id}</h2>
              <dl>
                <dt>Modelo</dt><dd>{texto(elegida.modelo)}</dd>
                <dt>Zona</dt><dd>{texto(elegida.zona)}</dd>
                <dt>Estado</dt><dd><span className="chip" style={{ background: colorMaquina(elegida) }}>{texto(elegida.estado)}</span></dd>
                <dt>Riesgo</dt><dd>{texto(typeof elegida.riesgo === 'object' ? elegida.riesgo?.nivel || elegida.riesgo?.nivel_riesgo : elegida.riesgo)}</dd>
                <dt>Horas de motor</dt><dd>{numero(elegida.horas_motor)}</dd>
                <dt>Última lectura</dt><dd>{fecha(elegida.ultima_lectura)}</dd>
              </dl>
              {variables && (
                <table className="tabla">
                  <tbody>
                    {Object.entries(variables)
                      .filter(([k, v]) => NOMBRE_VARIABLE[k] && v !== null && typeof v !== 'object')
                      .map(([k, v]) => <tr key={k}><td>{NOMBRE_VARIABLE[k]}</td><td>{numero(v)}</td></tr>)}
                  </tbody>
                </table>
              )}
            </>
          ) : (
            <p className="tenue">Selecciona una máquina en el mapa.</p>
          )}
          <h3>Máquinas</h3>
          <ul className="lista">
            {maquinas.map((m) => (
              <li key={m.maquina_id} className={m.maquina_id === seleccion ? 'activo' : ''} onClick={() => setSeleccion(m.maquina_id)}>
                <i style={{ background: colorMaquina(m) }} /> {texto(m.maquina_id)} <span className="tenue">{texto(m.zona)}</span>
              </li>
            ))}
          </ul>
        </aside>
      </div>
    </Cargando>
  )
}
