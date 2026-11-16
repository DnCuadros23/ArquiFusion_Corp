import { useState } from 'react'
import { USA_MOCK, api } from '../api.js'

export default function Login({ onEntrar }) {
  const [usuario, setUsuario] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [cargando, setCargando] = useState(false)

  async function enviar(e) {
    e.preventDefault()
    setError('')
    setCargando(true)
    try {
      onEntrar(await api.login(usuario.trim(), password))
    } catch (err) {
      setError(err.message)
    } finally {
      setCargando(false)
    }
  }

  return (
    <div className="login">
      <form onSubmit={enviar} className="tarjeta">
        <h1>ArquiFusion Fleet</h1>
        <p className="tenue">Gestión de flotas de maquinaria pesada</p>
        <label>Usuario<input value={usuario} onChange={(e) => setUsuario(e.target.value)} autoFocus required /></label>
        <label>Contraseña<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required /></label>
        {error && <p className="error">{error}</p>}
        <button disabled={cargando}>{cargando ? 'Entrando…' : 'Entrar'}</button>
        {USA_MOCK && <p className="tenue pequeno">Demo: tecnico, supervisor o gerente · clave demo123</p>}
      </form>
    </div>
  )
}
