import { Autocomplete, GoogleMap, MarkerF, useJsApiLoader } from '@react-google-maps/api';
import { useEffect, useMemo, useRef, useState } from 'react';

const GOOGLE_MAPS_LIBRARIES = ['places'];
const DEFAULT_CENTER = { lat: 6.2442, lng: -75.5812 };
const MAP_CONTAINER_STYLE = { width: '100%', height: '260px' };
const MAP_OPTIONS = {
  mapTypeControl: false,
  streetViewControl: false,
  fullscreenControl: false,
};

const toNumber = (value) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

const getGoogleMapsApiKey = () => (
  import.meta.env.VITE_GOOGLE_MAPS_API_KEY
  || import.meta.env.VITE_GOOGLE_MAPS_KEY
  || import.meta.env.VITE_GOOGLE_API_KEY
  || ''
).trim().replace(/^["']|["']$/g, '');

export const AddressAutocompleteMap = ({
  label = 'Direccion',
  placeholder = 'Ej: Cra 70 #45 Medellin',
  value,
  latitude,
  longitude,
  onChange,
  required = true,
}) => {
  const autocompleteRef = useRef(null);
  const geocodeTimerRef = useRef(null);
  const lastSelectedAddressRef = useRef('');
  const [statusMessage, setStatusMessage] = useState('');

  const apiKey = getGoogleMapsApiKey();
  const { isLoaded, loadError } = useJsApiLoader({
    id: 'ruta-facil-google-maps',
    googleMapsApiKey: apiKey || '',
    libraries: GOOGLE_MAPS_LIBRARIES,
  });

  const markerPosition = useMemo(() => {
    const lat = toNumber(latitude);
    const lng = toNumber(longitude);
    if (lat === null || lng === null) return null;
    return { lat, lng };
  }, [latitude, longitude]);

  const center = markerPosition || DEFAULT_CENTER;

  useEffect(() => () => {
    if (geocodeTimerRef.current) {
      clearTimeout(geocodeTimerRef.current);
    }
  }, []);

  const updateAddress = (nextAddress) => {
    onChange?.({ address: nextAddress, lat: latitude, lng: longitude });

    if (!isLoaded || !window.google || nextAddress.trim().length < 8) return;
    if (nextAddress === lastSelectedAddressRef.current) return;

    if (geocodeTimerRef.current) {
      clearTimeout(geocodeTimerRef.current);
    }

    geocodeTimerRef.current = setTimeout(() => {
      setStatusMessage('Buscando direccion...');
      const geocoder = new window.google.maps.Geocoder();
      geocoder.geocode(
        {
          address: `${nextAddress}, Colombia`,
          componentRestrictions: { country: 'CO' },
        },
        (results, status) => {
          if (status === 'OK' && results?.[0]?.geometry?.location) {
            const place = results[0];
            const location = place.geometry.location;
            const resolvedAddress = place.formatted_address || nextAddress;
            lastSelectedAddressRef.current = resolvedAddress;
            onChange?.({
              address: resolvedAddress,
              lat: location.lat(),
              lng: location.lng(),
            });
            setStatusMessage('Coordenadas detectadas automaticamente.');
          } else {
            setStatusMessage('No se encontro la direccion. Selecciona una sugerencia mas especifica.');
          }
        },
      );
    }, 850);
  };

  const handlePlaceChanged = () => {
    const place = autocompleteRef.current?.getPlace();
    const location = place?.geometry?.location;
    if (!location) {
      setStatusMessage('Selecciona una sugerencia valida de Google Maps.');
      return;
    }

    const nextAddress = place.formatted_address || place.name || value;
    lastSelectedAddressRef.current = nextAddress;
    onChange?.({
      address: nextAddress,
      lat: location.lat(),
      lng: location.lng(),
    });
    setStatusMessage('Direccion seleccionada y coordenadas actualizadas.');
  };

  const handleMarkerDragEnd = (event) => {
    onChange?.({
      address: value,
      lat: event.latLng.lat(),
      lng: event.latLng.lng(),
    });
    setStatusMessage('Marcador movido manualmente; coordenadas actualizadas.');
  };

  if (!apiKey) {
    return (
      <div className="form-group">
        <label>{label}</label>
        <input value={value} onChange={(event) => updateAddress(event.target.value)} required={required} />
        <div className="error-message mt-4">
          Falta configurar VITE_GOOGLE_MAPS_API_KEY en el archivo .env del frontend.
        </div>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="form-group">
        <label>{label}</label>
        <input value={value} onChange={(event) => updateAddress(event.target.value)} required={required} />
        <div className="error-message mt-4">
          Google Maps no pudo cargar Places. Verifica la API key, Places API, Geocoding API y restricciones.
        </div>
      </div>
    );
  }

  return (
    <div className="address-picker">
      <div className="form-group">
        <label>{label}</label>
        {!isLoaded ? (
          <input value={value} onChange={(event) => updateAddress(event.target.value)} placeholder="Cargando Google Places..." />
        ) : (
          <Autocomplete
            onLoad={(autocomplete) => {
              autocompleteRef.current = autocomplete;
              autocomplete.setComponentRestrictions({ country: ['co'] });
            }}
            onPlaceChanged={handlePlaceChanged}
          >
            <input
              type="text"
              value={value}
              onChange={(event) => updateAddress(event.target.value)}
              placeholder={placeholder}
              required={required}
            />
          </Autocomplete>
        )}
        {statusMessage && <p className="hint-text">{statusMessage}</p>}
      </div>

      <div className="coordinate-preview">
        <label>
          Latitud
          <input value={markerPosition?.lat ?? ''} readOnly placeholder="Autocompletada" />
        </label>
        <label>
          Longitud
          <input value={markerPosition?.lng ?? ''} readOnly placeholder="Autocompletada" />
        </label>
      </div>

      <div className="mini-map-shell">
        {!isLoaded ? (
          <div className="empty-state">Cargando mapa...</div>
        ) : (
          <GoogleMap
            mapContainerStyle={MAP_CONTAINER_STYLE}
            center={center}
            zoom={markerPosition ? 15 : 12}
            options={MAP_OPTIONS}
          >
            {markerPosition && (
              <MarkerF
                position={markerPosition}
                draggable
                title="Arrastra para ajustar la ubicacion"
                onDragEnd={handleMarkerDragEnd}
              />
            )}
          </GoogleMap>
        )}
      </div>
    </div>
  );
};
