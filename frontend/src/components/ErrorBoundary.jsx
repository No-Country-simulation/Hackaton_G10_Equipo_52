import { Component } from 'react';
import Boton from './ui/Boton';

// Si algún componente falla al dibujarse, muestra este aviso en vez de dejar la pantalla en blanco
export default class ErrorBoundary extends Component {
  state = { fallo: false };

  static getDerivedStateFromError() {
    return { fallo: true };
  }

  componentDidCatch(error, info) {
    console.error('Error en la interfaz:', error, info);
  }

  render() {
    if (!this.state.fallo) return this.props.children;
    return (
      <main style={{ maxWidth: 480, margin: '120px auto', padding: 24, textAlign: 'center' }}>
        <h1>Algo salió mal</h1>
        <p style={{ margin: '12px 0 24px' }}>
          Ocurrió un error inesperado en la aplicación. Recarga la página para volver a empezar.
        </p>
        <Boton iconoIzq="RotateCcw" onClick={() => window.location.reload()}>
          Recargar la página
        </Boton>
      </main>
    );
  }
}