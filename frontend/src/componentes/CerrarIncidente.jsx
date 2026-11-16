import { useState } from 'react'
import { api } from '../api.js'

export default function CerrarIncidente({ id, cancelar, listo }) {
  const [intervencion, setIntervencion] = useState('')
  const [componentes, setComponentes] = useState('')
  const [falla, setFalla] = useState(false)
  const [minutos, setMinutos] = useState('')
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)

  async function enviar(e) {
    e.preventDefault()
    const min = Number(minutos)
    if (!intervencion.trim()) return setError('Describe la intervención realizada')
    if (!Number.isFinite(min) || min < 0) return setError('Minutos detenida debe ser un número mayor o igual a 0')
    setError('')
    setEnviando(true)
    try {
      await api.cerrarIncidente(id, {
        intervencion: intervencion.trim(),
        componentes_reemplazados: componentes.split(',').map((c) => c.trim()).filter(Boolean),
        falla_confirmada: falla,
        minutos_detenida: min,
      })
      listo()
    } catch (err) {
      setError(err.message)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <form className="tarjeta formulario" onSubmit={enviar}>
      <h3>Cerrar incidente</h3>
      <label>Intervención realizada<textarea value={intervencion} onChange={(e) => setIntervencion(e.target.value)} rows={3} /></label>
      <label>Componentes reemplazados (separados por coma)<input value={componentes} onChange={(e) => setComponentes(e.target.value)} placeholder="FILTRO-AIRE-320" /></label>
      <label>Minutos detenida<input type="number" min="0" value={minutos} onChange={(e) => setMinutos(e.target.value)} /></label>
      <label className="check"><input type="checkbox" checked={falla} onChange={(e) => setFalla(e.target.checked)} /> Confirmo que hubo una falla (lo decide el técnico)</label>
      {error && <p className="error">{error}</p>}
      <div className="acciones">
        <button disabled={enviando}>{enviando ? 'Cerrando…' : 'Confirmar cierre'}</button>
        <button type="button" className="secundario" onClick={cancelar}>Cancelar</button>
      </div>
    </form>
  )
}
