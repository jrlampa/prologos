import React, { useState } from 'react';
import { api } from '../services/api';

const Simulador = ({ juizId }) => {
    const [file, setFile] = useState(null);
    const [parecer, setParecer] = useState('');
    const [loading, setLoading] = useState(false);

    const handleFileChange = (event) => {
        setFile(event.target.files[0]);
    };

    const handleAnalise = () => {
        if (!file || !juizId) {
            alert("Por favor, selecione um juiz e um ficheiro.");
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        setLoading(true);
        api.post(`/analise/peticao?juiz_id=${juizId}`, formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        })
            .then(response => {
                setParecer(response.data.parecer);
            })
            .catch(error => console.error("Erro ao analisar petição:", error))
            .finally(() => setLoading(false));
    };

    return (
        <div className="p-4 bg-white rounded-lg shadow-md mt-4">
            <h2 className="text-xl font-bold mb-4">Simulador de Análise de Petição</h2>
            <div className="flex items-center space-x-4">
                <input type="file" onChange={handleFileChange} className="file-input file-input-bordered w-full max-w-xs" />
                <button onClick={handleAnalise} className="btn btn-primary" disabled={loading}>
                    {loading ? <span className="loading loading-spinner"></span> : "Analisar Petição"}
                </button>
            </div>
            {parecer && (
                <div className="mt-4 p-4 border rounded-md bg-gray-50">
                    <h3 className="font-bold">Parecer da IA:</h3>
                    <p className="whitespace-pre-wrap">{parecer}</p>
                </div>
            )}
        </div>
    );
};

export default Simulador;