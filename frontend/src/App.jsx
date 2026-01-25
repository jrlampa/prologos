import React, { useCallback, useEffect, useState } from 'react';
import Dashboard from './components/Dashboard';
import Simulador from './components/Simulador';
import { api } from './services/api';

function App() {
    const [juizes, setJuizes] = useState([]);
    const [selectedJuiz, setSelectedJuiz] = useState('');
    const [juizStats, setJuizStats] = useState(null);
    const [loading, setLoading] = useState(false);
    const [dossie, setDossie] = useState('');
    const [dossieLoading, setDossieLoading] = useState(false);
    const [dossieError, setDossieError] = useState('');

    useEffect(() => {
        api.get('/juizes').then(res => setJuizes(res.data));
    }, []);

    useEffect(() => {
        if (selectedJuiz) {
            setLoading(true);
            setDossie('');
            setDossieError('');
            api.get(`/juiz/${selectedJuiz}/stats`)
                .then(res => setJuizStats(res.data))
                .finally(() => setLoading(false));
        } else {
            setJuizStats(null);
            setDossie('');
            setDossieError('');
        }
    }, [selectedJuiz]);

    const handleGerarDossie = useCallback(async () => {
        if (!selectedJuiz) return;
        setDossieLoading(true);
        setDossieError('');
        try {
            const res = await api.post(`/juiz/${selectedJuiz}/dossie`);
            setDossie(res.data?.dossie || '');
        } catch (e) {
            setDossieError(e?.response?.data?.detail || e?.message || 'Falha ao gerar dossiê.');
        } finally {
            setDossieLoading(false);
        }
    }, [selectedJuiz]);

    return (
        <div className="bg-gray-900 text-white min-h-screen p-8">
            <header className="text-center mb-10">
                <h1 className="text-4xl font-bold">PRÓLOGOS</h1>
                <p className="text-xl text-gray-400">Análise Jurimétrica e Previsão de Decisões</p>
            </header>

            <div className="max-w-4xl mx-auto">
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
                        <Dashboard
                            stats={juizStats}
                            dossie={dossie}
                            dossieLoading={dossieLoading}
                            dossieError={dossieError}
                            onGerarDossie={handleGerarDossie}
                        />
                        <Simulador juizId={selectedJuiz} dossie={dossie} />
                    </div>
                )}
            </div>
        </div>
    );
}

export default App;
