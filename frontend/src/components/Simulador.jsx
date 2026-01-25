import React, { useState } from 'react';
import { api } from '../services/api';

const Simulador = ({ juizId, dossie }) => {
    const [file, setFile] = useState(null);
    const [analise, setAnalise] = useState('');
    const [loading, setLoading] = useState(false);
    const [parecer, setParecer] = useState('');
    const [parecerLoading, setParecerLoading] = useState(false);
    const [parecerError, setParecerError] = useState('');

    const handleFileChange = (e) => {
        setFile(e.target.files[0]);
    };

    const handleAnalisar = () => {
        if (!file || !juizId) return;

        const formData = new FormData();
        formData.append('file', file);

        setLoading(true);
        api.post('/analise/peticao', formData, {
            params: { juiz_id: juizId },
            headers: {
                'Content-Type': 'multipart/form-data'
            }
        })
        .then(res => setAnalise(res.data.parecer))
        .catch(err => console.error(err))
        .finally(() => setLoading(false));
    };

    const handleParecer = () => {
        if (!file || !juizId) return;

        const formData = new FormData();
        formData.append('file', file);
        if (dossie) formData.append('dossie', dossie);

        setParecerLoading(true);
        setParecerError('');
        api.post('/analise/peticao/parecer', formData, {
            params: { juiz_id: juizId },
            headers: {
                'Content-Type': 'multipart/form-data'
            }
        })
        .then(res => setParecer(res.data.parecer))
        .catch(err => setParecerError(err?.response?.data?.detail || err?.message || 'Falha ao gerar parecer.'))
        .finally(() => setParecerLoading(false));
    };

    return (
        <div className="bg-gray-800 p-6 rounded-lg">
            <h2 className="text-2xl font-bold mb-4">Simulador de Afinidade</h2>
            <div className="space-y-4">
                <div>
                    <label htmlFor="peticao-upload" className="block mb-2 text-sm font-medium">Upload da Petição (PDF):</label>
                    <input type="file" id="peticao-upload" onChange={handleFileChange} className="block w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"/>
                </div>
                <button 
                    onClick={handleAnalisar} 
                    disabled={!file || loading}
                    className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-500 text-white font-bold py-2 px-4 rounded"
                >
                    {loading ? 'Analisando...' : 'Analisar Afinidade'}
                </button>

                {analise && (
                    <div className="mt-4 bg-gray-700 p-4 rounded">
                        <h3 className="font-bold mb-2">Resultado da Análise:</h3>
                        <pre className="whitespace-pre-wrap text-sm">{analise}</pre>
                    </div>
                )}

                <div className="pt-4 border-t border-gray-700">
                    <h3 className="text-xl font-bold mb-2">Consultor Jurídico IA (Groq)</h3>
                    <p className="text-sm text-gray-300 mb-3">
                        Gera um parecer estratégico (opcionalmente usando o dossiê do juiz).
                    </p>

                    <button
                        onClick={handleParecer}
                        disabled={!file || parecerLoading}
                        className="w-full bg-emerald-600 hover:bg-emerald-700 disabled:bg-gray-500 text-white font-bold py-2 px-4 rounded"
                    >
                        {parecerLoading ? 'Gerando parecer...' : 'Gerar Parecer Estratégico'}
                    </button>

                    {parecerError && (
                        <div className="mt-4 bg-red-900/40 border border-red-800 p-3 rounded">
                            <p className="text-sm text-red-200">{parecerError}</p>
                        </div>
                    )}

                    {parecer && (
                        <div className="mt-4 bg-gray-700 p-4 rounded">
                            <h3 className="font-bold mb-2">Parecer:</h3>
                            <pre className="whitespace-pre-wrap text-sm">{parecer}</pre>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default Simulador;
