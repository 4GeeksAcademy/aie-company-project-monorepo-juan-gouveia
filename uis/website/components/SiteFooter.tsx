const NEW_TAB_NOTE_ID = "new-tab-note";

const SOCIAL_LINK_CLASS =
  "inline-flex h-9 w-9 items-center justify-center rounded-md border border-red-300 text-red-700 hover:bg-red-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700 focus-visible:ring-offset-2";

export default function SiteFooter({ showSocialLinks = true }: { showSocialLinks?: boolean }) {
  return (
    <footer className="bg-gray-100 border-t border-red-200 mx-auto max-w-6xl px-3 py-4 md:px-4 lg:px-8">
      <span id={NEW_TAB_NOTE_ID} className="sr-only">
        Se abre en una pestaña nueva.
      </span>

      <div className="flex items-center justify-between gap-3">
        <p className="text-sm text-gray-600">
          &copy; 2026 Brasaland.{" "}
          <span className="block sm:inline sm:ml-1">Todos los derechos reservados.</span>
        </p>

        {showSocialLinks && (
          <div className="flex items-center gap-2 shrink-0">
            <a
              href="https://facebook.com/tu-cuenta-real"
              target="_blank"
              rel="noopener noreferrer"
              aria-label="Facebook de Brasaland"
              aria-describedby={NEW_TAB_NOTE_ID}
              className={SOCIAL_LINK_CLASS}
            >
              <svg aria-hidden="true" viewBox="0 0 24 24" className="h-4 w-4 fill-current">
                <path d="M13.5 22v-8h2.7l.4-3h-3.1V9.1c0-.9.3-1.5 1.6-1.5h1.7V5c-.3 0-1.4-.1-2.6-.1-2.6 0-4.3 1.6-4.3 4.5V11H7v3h2.8v8h3.7z" />
              </svg>
              <span className="sr-only">Facebook</span>
            </a>

            <a
              href="https://instagram.com/tu-cuenta-real"
              target="_blank"
              rel="noopener noreferrer"
              aria-label="Instagram de Brasaland"
              aria-describedby={NEW_TAB_NOTE_ID}
              className={SOCIAL_LINK_CLASS}
            >
              <svg aria-hidden="true" viewBox="0 0 24 24" className="h-4 w-4 fill-current">
                <path d="M7.75 2h8.5A5.75 5.75 0 0 1 22 7.75v8.5A5.75 5.75 0 0 1 16.25 22h-8.5A5.75 5.75 0 0 1 2 16.25v-8.5A5.75 5.75 0 0 1 7.75 2zm0 1.8A3.95 3.95 0 0 0 3.8 7.75v8.5a3.95 3.95 0 0 0 3.95 3.95h8.5a3.95 3.95 0 0 0 3.95-3.95v-8.5a3.95 3.95 0 0 0-3.95-3.95h-8.5z" />
                <path d="M12 7a5 5 0 1 1 0 10 5 5 0 0 1 0-10zm0 1.8A3.2 3.2 0 1 0 12 15.2 3.2 3.2 0 0 0 12 8.8z" />
                <circle cx="17.6" cy="6.4" r="1.2" />
              </svg>
              <span className="sr-only">Instagram</span>
            </a>
          </div>
        )}
      </div>
    </footer>
  );
}
