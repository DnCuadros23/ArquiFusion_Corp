import { useState } from 'react'
import { api } from '../api.js'
import { usarDatos } from './usarDatos.js'
import Cargando from './Cargando.jsx'
import CerrarIncidente from './CerrarIncidente.jsx'
import { NOMBRE_VARIABLE, fecha, numero } from './util.js'

export default function DetalleIncidente({ id, sesion, soloLectura, volver, respaldo }) {
  // Si la API no responde (modo degradado), se muestra lo que ya vino en la lista
  const estado = usarDatos(async () => {
    try {
      return await api.incidente(id)
    } catch (e) {
      if (respaldo) return respaldo
      throw e
    }
  }, [id])
  const [cerrando, setCerrando] = useState(false)
  const i = estado.datos
  const ia = i?.analisis_ia
  const abierto = i && !['CERRADO', 'DESCARTADO'].includes(i.estado)
  const puedeCerrar = (sesion.rol === 'tecnico' || sesion.rol === 'supervisor') && abierto && !soloLectura
  const tecnico = sesion.rol !== 'gerente'   // el gerente ve menos detalle técnico

  return (
    <div>
      <button className="secundario" onClick={volver}>← Volver</button>
      <Cargando estado={estado}>
        {i && (
          <div className="detalle">
            <h2>
              {i.maquina_id} <span className="tenue">{i.modelo} · {i.zona}</span>{' '}
              <span className={`chip sev-${i.severidad}`}>{i.severidad}</span> <span className="chip">{i.estado}</span>
              {i.grupo_causa_comun && <span className="chip causa">Posible causa común ({i.grupo_causa_comun})</span>}
            </h2>
            <p className="tenue">Detectado: {fecha(i.creado_ts)}</p>

            <div className="columnas">
              <section className="tarjeta">
                <h3>Análisis de la IA</h3>
                {ia ? (
                  <>
                    <p className="aviso amarillo pequeno">No es un diagnóstico confirmado. Indica qué merece revisión.</p>
                    <p><b>Riesgo:</b> {ia.nivel_riesgo} · <b>Especialidad sugerida:</b> {ia.especialidad_sugerida} · <span className="tenue">fuente: {ia.fuente}</span></p>
                    <p>{ia.resumen}</p>
                    {ia.mensajes_por_rol?.[sesion.rol] && <p className="mensaje-rol"><b>Para ti ({sesion.rol}):</b> {ia.mensajes_por_rol[sesion.rol]}</p>}
                    {tecnico && ia.posibles_causas_a_revisar?.length > 0 && (
                      <>
                        <b>Causas a revisar</b>
                        <ul>{ia.posibles_causas_a_revisar.map((c) => <li key={c}>{c}</li>)}</ul>
                      </>
                    )}
                  </>
                ) : <p className="tenue">Análisis pendiente.</p>}
              </section>

              {tecnico && (
                <section className="tarjeta">
                  <h3>Variables anómalas</h3>
                  <table>
                    <thead><tr><th>Variable</th><th>Valor</th><th>Habitual</th><th>z</th><th>Minutos</th></tr></thead>
                    <tbody>
                      {(i.variables_anomalas || []).map((v) => (
                        <tr key={v.variable}>
                          <td>{NOMBRE_VARIABLE[v.variable] || v.variable}</td>
                          <td><b>{numero(v.valor)}</b></td>
                          <td>{numero(v.media_habitual)}</td>
                          <td>{numero(v.z)}σ</td>
                          <td>{v.minutos_persistente ?? '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </section>
              )}

              <section className="tarjeta">
                <h3>Técnico asignado</h3>
                {i.tecnico_asignado ? (
                  <>
                    <p><b>{i.tecnico_asignado.nombre}</b> ({i.tecnico_asignado.especialidad}) · llegada estimada {i.tecnico_asignado.eta_min} min</p>
                    {tecnico && <p className="tenue">Por qué: {i.tecnico_asignado.razon}</p>}
                  </>
                ) : <p className="tenue">Sin asignar.</p>}
                <h3>Repuestos</h3>
                {i.repuestos?.length ? (
                  <ul>
                    {i.repuestos.map((r) => (
                      <li key={r.repuesto_id}>
                        {r.repuesto_id} × {r.cantidad} en {r.almacen}{' '}
                        {r.disponible ? <span className="chip ok">disponible</span> : <span className="chip sev-CRITICA">sin stock</span>}
                      </li>
                    ))}
                  </ul>
                ) : <p className="tenue">No se reservaron repuestos.</p>}
              </section>

              <section className="tarjeta">
                <h3>Línea de tiempo</h3>
                <ol className="tiempo">
                  {(i.linea_tiempo || []).map((e, n) => (
                    <li key={n}><b>{e.evento}</b> <span className="tenue">{fecha(e.ts)}</span>{e.detalle && <div>{e.detalle}</div>}</li>
                  ))}
                </ol>
                {i.cierre && (
                  <div className="cierre">
                    <h3>Cierre</h3>
                    <p>{i.cierre.intervencion}</p>
                    <p className="tenue">
                      Detenida {i.cierre.minutos_detenida ?? '—'} min · falla confirmada por el técnico: {i.cierre.falla_confirmada ? 'sí' : 'no'}
                      {i.cierre.componentes_reemplazados?.length ? ` · componentes: ${i.cierre.componentes_reemplazados.join(', ')}` : ''}
                    </p>
                  </div>
                )}
              </section>
            </div>

            {puedeCerrar && !cerrando && <button onClick={() => setCerrando(true)}>Cerrar incidente</button>}
            {cerrando && <CerrarIncidente id={i.incidente_id} cancelar={() => setCerrando(false)} listo={() => { setCerrando(false); estado.recargar() }} />}
          </div>
        )}
      </Cargando>
    </div>
  )
}
