import React, { useState } from 'react';
import axios from 'axios';

const API_URL = 'http://127.0.0.1:8000/api';

const ClonarJuiz = ({ onJuizClonado }) => {
    const [numeroProcesso, setNumeroProcesso] = useState('');
    const [loading, setLoading] = useState(false);
    const [mensagem, setMensagem] = useState(null);
    const [erro, setErro] = useState(null);

    const handleClonar = () => {
        if (!numeroProcesso.trim()) return;
        setLoading(true);
        setMensagem(null);
        setErro(null);

        axios.post(`${API_URL}/clonar-juiz`, { numero_processo: numeroProcesso })
            .then(res => {
                setMensagem(`✅ Juiz "${res.data.nome}" clonado com sucesso!`);
                if (onJuizClonado) onJuizClonado(res.data);
            })
            .catch(err => {
                const detail = err.response?.data?.detail || 'Erro ao clonar juiz.';
                setErro(`❌ ${detail}`);
            })
            .finally(() => setLoading(false));
    };

    return (
        <div className="bg-gray-800 p-4 rounded-lg mb-6">
            <h2 className="text-lg font-semibold mb-3">🧬 Clonar Perfil de Juiz</h2>
            <div className="flex gap-2">
                <input
                    type="text"
                    value={numeroProcesso}
                    onChange={(e) => setNumeroProcesso(e.target.value)}
                    placeholder="Nº do processo CNJ (ex: 1002345-88.2023.8.26.0100)"
                    className="flex-1 bg-gray-700 border border-gray-600 text-white text-sm rounded-lg p-2.5"
                />
                <button
                    onClick={handleClonar}
                    disabled={loading || !numeroProcesso.trim()}
                    className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-500 text-white font-bold py-2 px-4 rounded-lg text-sm"
                >
                    {loading ? 'Clonando...' : '🔍 Clonar'}
                </button>
            </div>
            {mensagem && <p className="mt-2 text-green-400 text-sm">{mensagem}</p>}
            {erro && <p className="mt-2 text-red-400 text-sm">{erro}</p>}
        </div>
    );
};

export default ClonarJuiz;
