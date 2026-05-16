import { api } from './api';

const toRadians = (degrees) => (degrees * Math.PI) / 180;

const calculateDistanceMeters = (pointA, pointB) => {
  const earthRadius = 6371000;
  const dLat = toRadians(pointB.lat - pointA.lat);
  const dLng = toRadians(pointB.lng - pointA.lng);

  const a = Math.sin(dLat / 2) ** 2
    + Math.cos(toRadians(pointA.lat))
    * Math.cos(toRadians(pointB.lat))
    * Math.sin(dLng / 2) ** 2;

  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return earthRadius * c;
};

export const startDriverLocationTracking = ({
  onPosition,
  onSent,
  onError,
  minDistanceMeters = 100,
  maxIntervalMs = 30000,
} = {}) => {
  if (!navigator.geolocation) {
    const error = new Error('Geolocalizacion no soportada por este navegador');
    if (onError) onError(error);
    return null;
  }

  let lastSentPoint = null;
  let lastSentAt = 0;

  const watchId = navigator.geolocation.watchPosition(
    async (position) => {
      const current = {
        lat: position.coords.latitude,
        lng: position.coords.longitude,
        accuracy: position.coords.accuracy,
        timestamp: position.timestamp,
      };

      if (onPosition) {
        onPosition(current);
      }

      const now = Date.now();
      const elapsed = now - lastSentAt;
      const moved = lastSentPoint
        ? calculateDistanceMeters(lastSentPoint, current)
        : Number.POSITIVE_INFINITY;

      const shouldSend = elapsed >= maxIntervalMs || moved >= minDistanceMeters;
      if (!shouldSend) {
        return;
      }

      try {
        await api.updateMyLocation(current.lat, current.lng);
        lastSentPoint = { lat: current.lat, lng: current.lng };
        lastSentAt = now;
        if (onSent) {
          onSent({ ...current, moved, elapsed });
        }
      } catch (err) {
        if (onError) onError(err);
      }
    },
    (geoError) => {
      const error = new Error(geoError.message || 'Error de geolocalizacion');
      if (onError) onError(error);
    },
    {
      enableHighAccuracy: true,
      timeout: 15000,
      maximumAge: 15000,
    },
  );

  return watchId;
};

export const stopDriverLocationTracking = (watchId) => {
  if (watchId !== null && watchId !== undefined) {
    navigator.geolocation.clearWatch(watchId);
  }
};
