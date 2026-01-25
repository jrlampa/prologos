import React from 'react';

const DEFAULT_TITLE = 'Termos de Uso (Beta) e Aviso Legal';

export default function TermsModal({ isOpen, onClose, title = DEFAULT_TITLE }) {
  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-label={title}
      onMouseDown={(e) => {
        // Fecha ao clicar no backdrop
        if (e.target === e.currentTarget) onClose?.();
      }}
    >
      <div className="absolute inset-0 bg-black/70" />

      <div className="relative w-full max-w-3xl rounded-lg border border-gray-700 bg-gray-900 shadow-xl">
        <div className="flex items-start justify-between gap-4 border-b border-gray-800 p-4">
          <div>
            <h2 className="text-lg font-bold text-white">{title}</h2>
            <p className="mt-1 text-xs text-gray-400">
              Última atualização: 25/01/2026
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded bg-gray-800 px-3 py-2 text-sm text-gray-200 hover:bg-gray-700"
            aria-label="Fechar"
          >
            Fechar
          </button>
        </div>

        <div className="max-h-[75vh] overflow-auto p-4 text-sm text-gray-200">
          <div className="space-y-4">
            <p className="text-gray-300">
              Este produto está em fase beta e fornece análises automatizadas e
              conteúdos gerados por IA como apoio informativo. Ao utilizar o
              sistema, você concorda com os termos abaixo.
            </p>

            <section>
              <h3 className="mb-2 text-base font-bold">1. Natureza informativa</h3>
              <ul className="list-disc space-y-1 pl-5 text-gray-300">
                <li>
                  As respostas podem conter imprecisões, omissões ou
                  desatualizações.
                </li>
                <li>
                  O conteúdo não constitui aconselhamento jurídico, parecer
                  profissional ou garantia de resultado.
                </li>
              </ul>
            </section>

            <section>
              <h3 className="mb-2 text-base font-bold">
                2. Não substitui avaliação humana
              </h3>
              <p className="text-gray-300">
                Use as saídas como ponto de partida e valide com profissional
                habilitado. Decisões jurídicas devem considerar o caso concreto,
                documentos, provas e jurisprudência aplicável.
              </p>
            </section>

            <section>
              <h3 className="mb-2 text-base font-bold">3. Uso responsável</h3>
              <ul className="list-disc space-y-1 pl-5 text-gray-300">
                <li>
                  Você é responsável por revisar o conteúdo antes de usar em
                  peças, petições ou recomendações.
                </li>
                <li>
                  É proibido usar o sistema para fins ilícitos, discriminatórios
                  ou para violar direitos de terceiros.
                </li>
              </ul>
            </section>

            <section>
              <h3 className="mb-2 text-base font-bold">
                4. Privacidade e LGPD (resumo)
              </h3>
              <ul className="list-disc space-y-1 pl-5 text-gray-300">
                <li>
                  Evite enviar dados pessoais sensíveis desnecessários em
                  documentos.
                </li>
                <li>
                  Recursos de IA podem envolver o envio de partes do conteúdo a
                  provedores externos (quando configurado). Consulte a política
                  de privacidade do ambiente de hospedagem.
                </li>
                <li>
                  O sistema pode registrar eventos técnicos (ex.: erros, tempo
                  de resposta) para melhoria e segurança.
                </li>
                <li>
                  O tratamento de dados deve observar a LGPD e as políticas do
                  ambiente onde o sistema está hospedado.
                </li>
              </ul>
            </section>

            <section>
              <h3 className="mb-2 text-base font-bold">
                5. Limitação de responsabilidade
              </h3>
              <p className="text-gray-300">
                Na extensão máxima permitida pela lei, os mantenedores não se
                responsabilizam por perdas decorrentes do uso das análises ou
                conteúdos gerados, incluindo decisões tomadas com base exclusiva
                nas saídas do sistema.
              </p>
            </section>

            <section>
              <h3 className="mb-2 text-base font-bold">6. Aceite</h3>
              <p className="text-gray-300">
                Ao marcar “Li e entendi os Termos”, você confirma ciência do
                aviso legal e concordância com estes termos.
              </p>
            </section>
          </div>
        </div>

        <div className="border-t border-gray-800 p-4 text-xs text-gray-400">
          Dica: para maior segurança, trate as saídas como rascunho e revise
          sempre antes de utilizar.
        </div>
      </div>
    </div>
  );
}

