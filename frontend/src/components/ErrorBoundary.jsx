import { Component } from 'react';

export class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, errorMessage: '' };
  }

  static getDerivedStateFromError(error) {
    return {
      hasError: true,
      errorMessage: error?.message || 'Se produjo un error inesperado.',
    };
  }

  componentDidCatch(error, errorInfo) {
    // eslint-disable-next-line no-console
    console.error('ErrorBoundary capturo un error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="panel" style={{ marginTop: 16, borderLeft: '4px solid #c62828' }}>
          <h2 style={{ marginTop: 0 }}>No se pudo cargar esta vista</h2>
          <p>{this.props?.fallbackMessage || 'Ocurrio un problema al renderizar el componente.'}</p>
          <p style={{ color: '#c62828' }}>{this.state.errorMessage}</p>
        </div>
      );
    }

    return this.props.children;
  }
}
