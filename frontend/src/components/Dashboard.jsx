import React from 'react';
import TermsAcceptanceGate from './TermsAcceptanceGate';

const Dashboard = ({
    stats,
    dossie,
    dossieLoading,
    dossieError,
    onGerarDossie,
    termsAccepted,
    onToggleTermsAccepted,
    onOpenTerms,
}) => {
    if (!stats) return null;

    return (
        <div className="bg-gray-800 p-6 rounded-lg">
            <h2 className="text-2xl font-bold mb-4">Dashboard do Juiz</h2>
            <div className="space-y-3">
                <p><span className="font-semibold">Nome:</span> {stats.nome}</p>
                <p><span className="font-semibold">Total de Decisões na Base:</span> {stats.total_decisoes}</p>
                {/* Outras estatísticas podem ser adicionadas aqui */}
            </div>

            <div className="mt-6 pt-6 border-t border-gray-700">
                <h3 className="text-xl font-bold mb-2">🧠 Dossiê Decisório (IA Generativa)</h3>
                <p className="text-sm text-gray-300 mb-4">
                    Gere um perfil comportamental do magistrado com base nos padrões de decisões armazenados.
                </p>

                <TermsAcceptanceGate
                    accepted={termsAccepted}
                    onChange={onToggleTermsAccepted}
                    onOpenTerms={onOpenTerms}
                    helperText="Para gerar o dossiê com IA, confirme o aceite dos Termos de Uso."
                />

                <button
                    onClick={onGerarDossie}
                    disabled={!termsAccepted || dossieLoading}
                    className="w-full bg-purple-600 hover:bg-purple-700 disabled:bg-gray-500 text-white font-bold py-2 px-4 rounded"
                >
                    {dossieLoading ? 'Gerando dossiê...' : 'Gerar Dossiê do Magistrado'}
                </button>

                {dossieError && (
                    <div className="mt-4 bg-red-900/40 border border-red-800 p-3 rounded">
                        <p className="text-sm text-red-200">{dossieError}</p>
                    </div>
                )}

                {dossie && (
                    <div className="mt-4 bg-gray-700 p-4 rounded">
                        <h4 className="font-bold mb-2">Dossiê:</h4>
                        <pre className="whitespace-pre-wrap text-sm">{dossie}</pre>
                    </div>
                )}
            </div>
        </div>
    );
};

export default Dashboard;
