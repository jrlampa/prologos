import axios from 'axios';

// Em dev, use `VITE_API_URL=/api` + proxy do Vite para o Express.
// Em prod, pode ser `/api` (mesma origem) ou uma URL absoluta.
const baseURL = import.meta.env.VITE_API_URL || '/api';

export const api = axios.create({
  baseURL,
});

export const API_BASE_URL = baseURL;

