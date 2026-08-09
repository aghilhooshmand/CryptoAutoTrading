export function NotFoundPage() {
  return (
    <section className="page" aria-labelledby="not-found-title">
      <h1 id="not-found-title">Not Found</h1>
      <p>
        This location is not part of CryptoAutoTrading. Use the primary
        navigation to open Dashboard, Auto Trading, or Portfolio.
      </p>
      <p className="note">
        Unsupported routes stay on this Not Found page. They are not silently
        redirected to a primary area.
      </p>
    </section>
  );
}
