import api from '../api/api'; // ajuste o caminho se necessário

export const login = async (username, password) => {
  try {
    const response = await api.post('/auth/token/', { username, password });
    
    localStorage.setItem('access', response.data.access);
    localStorage.setItem('refresh', response.data.refresh);
    
    return response.data;
  } catch (error) {
    throw new Error('Credenciais inválidas');
  }
};

export const register = async (userData) => {
  try {
    const response = await api.post('/auth/register/', userData);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.error || 'Erro ao registrar');
  }
};

export const logout = () => {
  localStorage.removeItem('access');
  localStorage.removeItem('refresh');
};

export const isAuthenticated = () => {
  return !!localStorage.getItem('access');
};

export const getAccessToken = () => {
  return localStorage.getItem('access');
};