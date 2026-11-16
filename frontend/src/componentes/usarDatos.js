import { useCallback, useEffect, useState } from 'react'

// Carga datos de la API y expone { datos, cargando, error, recargar }
export function usarDatos(cargar, dependencias = []) {
  const [estado, setEstado] = useState({ datos: null, cargando: true, error: '' })

  const recargar = useCallback(async () => {
    setEstado((s) => ({ ...s, cargando: true, error: '' }))
    try {
      setEstado({ datos: await cargar(), cargando: false, error: '' })
    } catch (e) {
      setEstado({ datos: null, cargando: false, error: e.message })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, dependencias)

  useEffect(() => { recargar() }, [recargar])
  return { ...estado, recargar }
}
