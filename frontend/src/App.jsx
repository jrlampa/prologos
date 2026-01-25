import React, { useCallback, useEffect, useState } from 'react';
import Dashboard from './components/Dashboard';
import Simulador from './components/Simulador';
import LegalDisclaimer from './components/LegalDisclaimer';
import TermsModal from './components/TermsModal';
import { api } from './services/api';

const TERMS_ACCEPTED_KEY = 'prologos_terms_acceptance_v1';
const TERMS_VERSION = '2026-01-25';

function App() {
    const [juizes, setJuizes] = useState([]);
    const [selectedJuiz, setSelectedJuiz] = useState('');
    const [juizStats, setJuizStats] = useState(null);
    const [loading, setLoading] = useState(false);
    const [dossie, setDossie] = useState('');
    const [dossieLoading, setDossieLoading] = useState(false);
    const [dossieError, setDossieError] = useState('');
    const [termsAccepted, setTermsAccepted] = useState(false);
    const [termsOpen, setTermsOpen] = useState(false);

    useEffect(() => {
        api.get('/juizes').then(res => setJuizes(res.data));
    }, []);

    useEffect(() => {
        try {
            const raw = localStorage.getItem(TERMS_ACCEPTED_KEY);
            if (!raw) return;
            const parsed = JSON.parse(raw);
            const ok = parsed?.accepted === true && parsed?.version === TERMS_VERSION;
            setTermsAccepted(ok);
        } catch {
            // no-op (ex.: localStorage indisponível)
        }
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
        if (!termsAccepted) {
            setTermsOpen(true);
            return;
        }
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
    }, [selectedJuiz, termsAccepted]);

    const handleToggleTermsAccepted = useCallback((next) => {
        setTermsAccepted(!!next);
        try {
            const payload = {
                accepted: !!next,
                version: TERMS_VERSION,
                acceptedAt: next ? new Date().toISOString() : null,
            };
            localStorage.setItem(TERMS_ACCEPTED_KEY, JSON.stringify(payload));
        } catch {
            // no-op
        }
    }, []);

    return (
        <div className="bg-gray-900 text-white min-h-screen p-8">
            <header className="text-center mb-10">
                <h1 className="text-4xl font-bold">PRÓLOGOS</h1>
                <p className="text-xl text-gray-400">Análise Jurimétrica e Previsão de Decisões</p>
            </header>

            <div className="max-w-4xl mx-auto">
                <LegalDisclaimer
                    accepted={termsAccepted}
                    onToggleAccepted={handleToggleTermsAccepted}
                    onOpenTerms={() => setTermsOpen(true)}
                />

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
                            termsAccepted={termsAccepted}
                            onToggleTermsAccepted={handleToggleTermsAccepted}
                            onOpenTerms={() => setTermsOpen(true)}
                        />
                        <Simulador
                            juizId={selectedJuiz}
                            dossie={dossie}
                            termsAccepted={termsAccepted}
                            onToggleTermsAccepted={handleToggleTermsAccepted}
                            onOpenTerms={() => setTermsOpen(true)}
                        />
                    </div>
                )}
            </div>

            <TermsModal isOpen={termsOpen} onClose={() => setTermsOpen(false)} />
        </div>
    );
}

export default App;
