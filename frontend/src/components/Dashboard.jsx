import React from 'react';

const Dashboard = ({ stats }) => {
    if (!stats) return null;

    return (
        <div className="bg-gray-800 p-6 rounded-lg">
            <h2 className="text-2xl font-bold mb-4">Dashboard do Juiz</h2>
            <div className="space-y-3">
                <p><span className="font-semibold">Nome:</span> {stats.nome}</p>
                <p><span className="font-semibold">Total de Decisões na Base:</span> {stats.total_decisoes}</p>
                {/* Outras estatísticas podem ser adicionadas aqui */}
            </div>
        </div>
    );
};

export default Dashboard;
