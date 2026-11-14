export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="auth">
      <section className="auth-hero">
        <div className="brand">
          <span className="brand-dot" aria-hidden>✚</span> MEDIAI
        </div>
        <div>
          <h1>L&apos;aide au diagnostic pensée pour la pratique médicale en Afrique.</h1>
          <p>
            Diagnostics différentiels pondérés et justifiés, décision de prise en charge, traitements conformes aux
            recommandations OMS et nationales, et un assistant clinique pour approfondir chaque cas.
          </p>
        </div>
        <p className="small" style={{ color: "rgba(255,255,255,.7)" }}>
          Outil d&apos;aide à la décision : il ne remplace pas le jugement clinique du médecin.
        </p>
      </section>
      <section className="auth-form">{children}</section>
    </div>
  );
}
