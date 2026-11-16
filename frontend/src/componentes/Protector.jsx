import { Component } from 'react'

// Si una vista falla al dibujarse, muestra el error en vez de dejar la pantalla en blanco.
export default class Protector extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    console.error('[ArquiFusion] Error en la vista:', error, info?.componentStack)
  }

  componentDidUpdate(prev) {
    if (prev.vista !== this.props.vista && this.state.error) this.setState({ error: null })
  }

  render() {
    if (this.state.error) {
      return (
        <div className="tarjeta">
          <h2>No se pudo mostrar esta vista</h2>
          <p className="error">{String(this.state.error.message || this.state.error)}</p>
          <button onClick={() => this.setState({ error: null })}>Reintentar</button>
        </div>
      )
    }
    return this.props.children
  }
}
