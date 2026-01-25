import React from 'react';

export default function TermsAcceptanceGate({
  accepted,
  onChange,
  onOpenTerms,
  helperText = 'Para usar recursos de IA, confirme que leu e entendeu os Termos de Uso.',
}) {
  if (accepted) return null;

  return (
    <div className="mb-4 rounded-lg border border-amber-800 bg-amber-900/20 p-3">
      <p className="text-sm text-amber-100">{helperText}</p>

      <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <label className="flex items-start gap-2 text-sm text-amber-100">
          <input
            type="checkbox"
            checked={!!accepted}
            onChange={(e) => onChange?.(e.target.checked)}
            className="mt-1 h-4 w-4 accent-amber-400"
          />
          <span>
            Li e entendi os{' '}
            <button
              type="button"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                onOpenTerms?.();
              }}
              className="underline underline-offset-2 hover:text-white"
            >
              Termos de Uso
            </button>
            .
          </span>
        </label>

        <button
          type="button"
          onClick={onOpenTerms}
          className="rounded bg-amber-700 px-3 py-2 text-sm font-semibold text-white hover:bg-amber-600"
        >
          Ler Termos
        </button>
      </div>
    </div>
  );
}

