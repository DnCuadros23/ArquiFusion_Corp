import { useEffect, useState } from 'react'
import { USA_MOCK, alCambiarModo, enModoDegradado, guardarSesion, leerSesion } from './api.js'
import Login from './componentes/Login.jsx'
import Flota from './componentes/Flota.jsx'
import Incidentes from './componentes/Incidentes.jsx'
import Tecnicos from './componentes/Tecnicos.jsx'
import Planificacion from './componentes/Planificacion.jsx'
import Protector from './componentes/Protector.jsx'

// Qué ve cada rol (contracts/interfaces.md §3)
const MENU = {
  tecnico: [['incidentes', 'Mis incidentes'], ['flota', 'Flota']],
  supervisor: [['flota', 'Flota'], ['incidentes', 'Incidentes'], ['tecnicos', 'Técnicos'], ['planificacion', 'Planificación']],
  gerente: [['planificacion', 'Resumen del día'], ['flota', 'Flota'], ['incidentes', 'Incidentes']],
}

export default function App() {
  const [sesion, setSesion] = useState(leerSesion)
  const [vista, setVista] = useState(null)
  const [degradado, setDegradado] = useState(enModoDegradado())

  useEffect(() => alCambiarModo(setDegradado), [])

  if (!sesion) {
    return <Login onEntrar={(s) => { guardarSesion(s); setSesion(s); setVista(MENU[s.rol]?.[0]?.[0]) }} />
  }

  const menu = MENU[sesion.rol] || MENU.supervisor
  const actual = vista || menu[0][0]
  const salir = () => { guardarSesion(null); setSesion(null); setVista(null) }

  return (
    <div className="app">
      <header className="barra">
        <strong className="marca">ArquiFusion Fleet</strong>
        <nav>
          {menu.map(([id, texto]) => (
            <button key={id} className={id === actual ? 'activo' : ''} onClick={() => setVista(id)}>{texto}</button>
          ))}
        </nav>
        <span className="usuario">{sesion.nombre} · {sesion.rol} · {sesion.tenant_id}</span>
        <button className="secundario" onClick={salir}>Salir</button>
      </header>

      {USA_MOCK && <div className="aviso azul">Datos de prueba (VITE_USE_MOCK). No hay conexión con AWS.</div>}
      {degradado && <div className="aviso amarillo">Modo degradado: datos desde la réplica en Google Firestore (solo lectura).</div>}

      <main>
        <Protector vista={actual}>
        {actual === 'flota' && <Flota />}
        {actual === 'incidentes' && <Incidentes sesion={sesion} soloLectura={degradado} />}
        {actual === 'tecnicos' && <Tecnicos />}
        {actual === 'planificacion' && <Planificacion rol={sesion.rol} />}
        </Protector>
      </main>
    </div>
  )
}
