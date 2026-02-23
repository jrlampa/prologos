import React from 'react';

const Dashboard = ({ stats }) => {
    if (!stats) return null;

    const temas = Object.entries(stats.distribuicao_temas || {}).sort((a, b) => b[1] - a[1]);
    const resultados = Object.entries(stats.distribuicao_resultados || {}).sort((a, b) => b[1] - a[1]);

    return (
        <div className="bg-gray-800 p-6 rounded-lg space-y-4">
            <h2 className="text-2xl font-bold mb-4">Dashboard do Juiz</h2>
            <div className="space-y-2">
                <p><span className="font-semibold">Nome:</span> {stats.nome}</p>
                {stats.vara && <p><span className="font-semibold">Vara:</span> {stats.vara}</p>}
                <p><span className="font-semibold">Total de Decisões:</span> {stats.total_decisoes}</p>
            </div>

            {temas.length > 0 && (
                <div>
                    <h3 className="text-lg font-semibold mb-2">Distribuição por Tema</h3>
                    <ul className="space-y-1 text-sm">
                        {temas.map(([tema, count]) => (
                            <li key={tema} className="flex justify-between">
                                <span className="text-gray-300">{tema}</span>
                                <span className="font-medium">{count}</span>
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {resultados.length > 0 && (
                <div>
                    <h3 className="text-lg font-semibold mb-2">Distribuição por Resultado</h3>
                    <ul className="space-y-1 text-sm">
                        {resultados.map(([resultado, count]) => (
                            <li key={resultado} className="flex justify-between">
                                <span className="text-gray-300">{resultado}</span>
                                <span className="font-medium">{count}</span>
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    );
};

export default Dashboard;
