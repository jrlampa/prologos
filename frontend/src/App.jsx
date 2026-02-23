import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import Dashboard from './components/Dashboard';
import Simulador from './components/Simulador';
import ClonarJuiz from './components/ClonarJuiz';

const API_URL = 'http://127.0.0.1:8000/api';

function App() {
    const [juizes, setJuizes] = useState([]);
    const [selectedJuiz, setSelectedJuiz] = useState('');
    const [juizStats, setJuizStats] = useState(null);
    const [loading, setLoading] = useState(false);

    const fetchJuizes = useCallback(() => {
        axios.get(`${API_URL}/juizes`).then(res => setJuizes(res.data));
    }, []);

    useEffect(() => {
        fetchJuizes();
    }, [fetchJuizes]);

    useEffect(() => {
        if (selectedJuiz) {
            setLoading(true);
            axios.get(`${API_URL}/juiz/${selectedJuiz}/stats`)
                .then(res => setJuizStats(res.data))
                .finally(() => setLoading(false));
        }
    }, [selectedJuiz]);

    const handleJuizClonado = (novoJuiz) => {
        fetchJuizes();
        setSelectedJuiz(String(novoJuiz.id));
    };

    return (
        <div className="bg-gray-900 text-white min-h-screen p-8">
            <header className="text-center mb-10">
                <h1 className="text-4xl font-bold">PRÓLOGOS</h1>
                <p className="text-xl text-gray-400">Análise Jurimétrica e Previsão de Decisões</p>
            </header>

            <div className="max-w-4xl mx-auto">
                <ClonarJuiz onJuizClonado={handleJuizClonado} />

                <div className="bg-gray-800 p-4 rounded-lg mb-6">
                    <label htmlFor="juiz-select" className="block mb-2 text-sm font-medium">Selecione o Juiz para Análise:</label>
                    <select 
                        id="juiz-select"
                        value={selectedJuiz}
                        onChange={(e) => setSelectedJuiz(e.target.value)}
                        className="bg-gray-700 border border-gray-600 text-white text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5"
                    >
                        <option value="">-- Escolha um Juiz --</option>
                        {juizes.map(juiz => (
                            <option key={juiz.id} value={juiz.id}>{juiz.nome}</option>
                        ))}
                    </select>
                </div>

                {loading && <p className="text-center">Carregando dados do juiz...</p>}

                {juizStats && (
                    <div className='grid grid-cols-1 md:grid-cols-2 gap-8'>
                        <Dashboard stats={juizStats} />
                        <Simulador juizId={selectedJuiz} />
                    </div>
                )}
            </div>
        </div>
    );
}

export default App;
