# Frontend Ruta Facil

Dashboard React + Vite para visualizacion de pedidos y repartidores.

## Google Maps

Este frontend usa `@react-google-maps/api` para mostrar mapa en vivo.

1. Crea un archivo `.env` dentro de `frontend`.
2. Agrega tu llave:

```env
VITE_GOOGLE_MAPS_API_KEY=tu_api_key_aqui
```

3. Asegura que la API key tenga habilitada la **Maps JavaScript API** en Google Cloud.

Si no existe una API key valida, el panel mostrara un mensaje de configuracion en lugar del mapa.

## Scripts

- `npm run dev`: entorno de desarrollo.
- `npm run build`: build de produccion.
- `npm run lint`: revisa lint.
