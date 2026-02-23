import React from 'react';

const Dashboard = ({ stats }) => {
    if (!stats) return null;

    return (
        <div className="bg-gray-800 p-6 rounded-lg">
            <h2 className="text-2xl font-bold mb-4">Dashboard do Juiz</h2>
            <div className="space-y-3">
                <p><span className="font-semibold">Nome:</span> {stats.nome}</p>
                <p><span className="font-semibold">Total de Decisões na Base:</span> {stats.total_decisoes}</p>
            </div>
            {stats.total_decisoes === 0 && (
                <p className="mt-4 text-yellow-400 text-sm">Nenhuma decisão coletada ainda. Clone um processo para popular a base.</p>
            )}
        </div>
    );
};

export default Dashboard;
