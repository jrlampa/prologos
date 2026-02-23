import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import axios from 'axios';
import App from './App';

// Mock axios
jest.mock('axios');

const mockJuizes = [
  { id: 1, nome: 'Juiz 1' },
  { id: 2, nome: 'Juiz 2' },
];

const mockJuizStats = {
  totalDecisoes: 100,
  deferidos: 60,
  indeferidos: 40,
};

describe('App', () => {
  beforeEach(() => {
    axios.get.mockImplementation((url) => {
      if (url.endsWith('/juizes')) {
        return Promise.resolve({ data: mockJuizes });
      }
      if (url.includes('/stats')) {
        return Promise.resolve({ data: mockJuizStats });
      }
      return Promise.reject(new Error('not found'));
    });
  });

  it('renders the header and fetches juizes on initial render', async () => {
    render(<App />);
    
    expect(screen.getByText('PRÓLOGOS')).toBeInTheDocument();
    expect(screen.getByText('Análise Jurimétrica e Previsão de Decisões')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('-- Escolha um Juiz --')).toBeInTheDocument();
      expect(screen.getByText('Juiz 1')).toBeInTheDocument();
      expect(screen.getByText('Juiz 2')).toBeInTheDocument();
    });
  });

  it('renders the ClonarJuiz section', async () => {
    render(<App />);
    expect(screen.getByText('🧬 Clonar Perfil de Juiz')).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Nº do processo CNJ/)).toBeInTheDocument();
    expect(screen.getByText('🔍 Clonar')).toBeInTheDocument();
  });

  it('shows loading message and fetches stats when a juiz is selected', async () => {
    render(<App />);
    
    await waitFor(() => {
        expect(screen.getByText('Juiz 1')).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText('Selecione o Juiz para Análise:'), {
      target: { value: '1' },
    });

    expect(screen.getByText('Carregando dados do juiz...')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.queryByText('Carregando dados do juiz...')).not.toBeInTheDocument();
      // Assuming Dashboard and Simulador will be rendered.
      // We can check for a text that is unique to one of those components.
      // For now, let's just check that the loading message is gone.
    });
  });

  it('calls clone endpoint and refreshes judges list on successful clone', async () => {
    const clonedJuiz = { id: 3, nome: 'Juiz Clonado', vara: '1ª Vara Cível' };
    axios.post = jest.fn().mockResolvedValueOnce({ data: clonedJuiz });
    axios.get.mockImplementation((url) => {
      if (url.endsWith('/juizes')) {
        return Promise.resolve({ data: [...mockJuizes, { id: 3, nome: 'Juiz Clonado' }] });
      }
      return Promise.reject(new Error('not found'));
    });

    render(<App />);

    fireEvent.change(screen.getByPlaceholderText(/Nº do processo CNJ/), {
      target: { value: '1002345-88.2023.8.26.0100' },
    });
    fireEvent.click(screen.getByText('🔍 Clonar'));

    await waitFor(() => {
      expect(axios.post).toHaveBeenCalledWith(
        expect.stringContaining('/clonar-juiz'),
        { numero_processo: '1002345-88.2023.8.26.0100' }
      );
    });

    await waitFor(() => {
      expect(screen.getByText(/Juiz Clonado/)).toBeInTheDocument();
    });
  });
});
