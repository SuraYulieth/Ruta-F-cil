import { Autocomplete, GoogleMap, MarkerF, useJsApiLoader } from '@react-google-maps/api';
import { useMemo, useRef, useState } from 'react';

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
  onAddressChange,
  onLocationChange,
  onChange,
  required = true,
}) => {
  const autocompleteRef = useRef(null);
  const [statusMessage, setStatusMessage] = useState('');

  const apiKey = getGoogleMapsApiKey();
  const { isLoaded, loadError } = useJsApiLoader({
    id: 'ruta-facil-google-maps',
    googleMapsApiKey: apiKey || '',
    libraries: GOOGLE_MAPS_LIBRARIES,
  });

  const addressValue = value || '';

  const markerPosition = useMemo(() => {
    const lat = toNumber(latitude);
    const lng = toNumber(longitude);
    if (lat === null || lng === null) return null;
    return { lat, lng };
  }, [latitude, longitude]);

  const center = markerPosition || DEFAULT_CENTER;

  const emitAddress = (nextAddress) => {
    onAddressChange?.(nextAddress);
  };

  const emitLocation = (nextLocation) => {
    onLocationChange?.(nextLocation);
  };

  const handleInputChange = (event) => {
    const nextAddress = event.target.value;
    emitAddress(nextAddress);
    emitLocation({ lat: '', lng: '' });
    onChange?.({ address: nextAddress, lat: '', lng: '' });
    setStatusMessage('Escribe y selecciona una sugerencia para obtener coordenadas.');
  };

  const handlePlaceChanged = () => {
    const place = autocompleteRef.current?.getPlace();
    const location = place?.geometry?.location;

    if (!location) {
      setStatusMessage('No se encontraron coordenadas para esa sugerencia. Puedes seguir escribiendo manualmente.');
      return;
    }

    const nextAddress = place.formatted_address || place.name || addressValue;
    const nextLocation = {
      lat: location.lat(),
      lng: location.lng(),
    };

    onAddressChange?.(nextAddress);
    onLocationChange?.(nextLocation);
    onChange?.({ address: nextAddress, ...nextLocation });
    setStatusMessage('Direccion seleccionada y coordenadas actualizadas.');
  };

  const handleMarkerDragEnd = (event) => {
    const nextLocation = {
      lat: event.latLng.lat(),
      lng: event.latLng.lng(),
    };
    emitLocation(nextLocation);
    onChange?.({ address: addressValue, ...nextLocation });
    setStatusMessage('Marcador movido manualmente; coordenadas actualizadas.');
  };

  const renderAddressInput = (message) => (
    <div className="form-group">
      <label>{label}</label>
      <input
        type="text"
        value={addressValue}
        onChange={handleInputChange}
        placeholder={placeholder}
        required={required}
        disabled={false}
        readOnly={false}
      />
      {message && <p className="hint-text">{message}</p>}
      {statusMessage && <p className="hint-text">{statusMessage}</p>}
    </div>
  );

  if (!apiKey) {
    return (
      <div className="address-picker">
        {renderAddressInput('Google Places no esta disponible, puedes escribir la direccion manualmente.')}
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="address-picker">
        {renderAddressInput('Google Places no esta disponible, puedes escribir la direccion manualmente.')}
      </div>
    );
  }

  return (
    <div className="address-picker">
      <div className="form-group">
        <label>{label}</label>
        {!isLoaded ? (
          <input
            type="text"
            value={addressValue}
            onChange={handleInputChange}
            placeholder="Cargando Google Places..."
            required={required}
            disabled={false}
            readOnly={false}
          />
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
              value={addressValue}
              onChange={handleInputChange}
              placeholder={placeholder}
              required={required}
              disabled={false}
              readOnly={false}
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
