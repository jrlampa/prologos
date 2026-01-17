import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { api } from '../services/api';

const Dashboard = ({ juizId }) => {
    const [data, setData] = useState(null);

    useEffect(() => {
        if (juizId) {
            api.get(`/dashboard/${juizId}`)
                .then(response => {
                    const chartData = Object.entries(response.data.distribuicao_temas).map(([name, value]) => ({ name, value }));
                    setData(chartData);
                })
                .catch(error => console.error("Erro ao buscar dados do dashboard:", error));
        }
    }, [juizId]);

    if (!data) return <div>Selecione um juiz para ver o dashboard.</div>;

    return (
        <div className="p-4 bg-white rounded-lg shadow-md">
            <h2 className="text-xl font-bold mb-4">Dashboard do Juiz</h2>
            <ResponsiveContainer width="100%" height={300}>
                <BarChart data={data}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="value" fill="#8884d8" name="Nº de Decisões" />
                </BarChart>
            </ResponsiveContainer>
        </div>
    );
};

export default Dashboard;