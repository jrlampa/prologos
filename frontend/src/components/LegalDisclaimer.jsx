import React from 'react';

export default function LegalDisclaimer({ accepted, onToggleAccepted, onOpenTerms }) {
  return (
    <div className="mb-6 rounded-lg border border-amber-800 bg-amber-900/20 p-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <p className="text-sm text-amber-100">
            <span className="font-bold">Aviso:</span> esta ferramenta fornece{' '}
            <span className="font-semibold">análises estatísticas e probabilísticas</span>.{' '}
            Não substitui o aconselhamento jurídico profissional nem garante resultados processuais.
          </p>
          <button
            type="button"
            onClick={onOpenTerms}
            className="mt-2 text-sm font-semibold text-amber-200 underline underline-offset-2 hover:text-white"
          >
            Ler Termos de Uso e Privacidade (LGPD)
          </button>
        </div>

        <label className="flex items-start gap-2 text-sm text-amber-100">
          <input
            type="checkbox"
            checked={!!accepted}
            onChange={(e) => onToggleAccepted?.(e.target.checked)}
            className="mt-1 h-4 w-4 accent-amber-400"
          />
          <span>
            Li e entendi os Termos.{' '}
            {!accepted && (
              <span className="text-amber-200">
                (Necessário para usar recursos de IA)
              </span>
            )}
          </span>
        </label>
      </div>
    </div>
  );
}

