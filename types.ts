export interface BusStop {
  stop_name: string;
  stop_id: string;
  stop_lat: number;
  stop_lon: number;
  distance?: number; // Calculated distance in km
  walkingTime?: number; // Estimated minutes
}

export interface MapState {
  hoverLat: number | null;
  hoverLng: number | null;
  nearestStops: BusStop[];
}

export enum DistanceMode {
  EUCLIDEAN = 'EUCLIDEAN',
  WALKING = 'WALKING'
}