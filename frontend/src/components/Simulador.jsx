import React, { useState } from 'react';
import axios from 'axios';

const API_URL = 'http://127.0.0.1:8000/api';

const Simulador = ({ juizId }) => {
    const [file, setFile] = useState(null);
    const [analise, setAnalise] = useState('');
    const [loading, setLoading] = useState(false);
    const [erro, setErro] = useState('');

    const handleFileChange = (e) => {
        setFile(e.target.files[0]);
        setErro('');
    };

    const handleAnalisar = () => {
        if (!file || !juizId) return;

        const formData = new FormData();
        formData.append('file', file);

        setLoading(true);
        setErro('');
        setAnalise('');
        axios.post(`${API_URL}/analise/peticao?juiz_id=${juizId}`, formData, {
            headers: {
                'Content-Type': 'multipart/form-data'
            }
        })
        .then(res => setAnalise(res.data.parecer))
        .catch(err => {
            const detail = err.response?.data?.detail;
            setErro(detail || 'Erro ao processar a petição. Tente novamente.');
        })
        .finally(() => setLoading(false));
    };

    return (
        <div className="bg-gray-800 p-6 rounded-lg">
            <h2 className="text-2xl font-bold mb-4">Simulador de Afinidade</h2>
            <div className="space-y-4">
                <div>
                    <label htmlFor="peticao-upload" className="block mb-2 text-sm font-medium">Upload da Petição (PDF):</label>
                    <input type="file" accept=".pdf" id="peticao-upload" onChange={handleFileChange} className="block w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"/>
                </div>
                <button 
                    onClick={handleAnalisar} 
                    disabled={!file || loading}
                    className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-500 text-white font-bold py-2 px-4 rounded"
                >
                    {loading ? 'Analisando...' : 'Analisar Afinidade'}
                </button>

                {erro && (
                    <div className="mt-2 bg-red-800 text-red-200 p-3 rounded text-sm">
                        {erro}
                    </div>
                )}

                {analise && (
                    <div className="mt-4 bg-gray-700 p-4 rounded">
                        <h3 className="font-bold mb-2">Resultado da Análise:</h3>
                        <pre className="whitespace-pre-wrap text-sm">{analise}</pre>
                    </div>
                )}
            </div>
        </div>
    );
};

export default Simulador;
