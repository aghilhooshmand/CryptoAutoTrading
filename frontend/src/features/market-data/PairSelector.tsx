import type { TradingPair } from "../../services/marketDataApi";

interface Props {
  pairs: TradingPair[];
  selectedSymbol: string | null;
  favorites: string[];
  search: string;
  onSearchChange: (value: string) => void;
  onSelect: (symbol: string) => void;
  onToggleFavorite: (symbol: string) => void;
}

export function PairSelector({
  pairs,
  selectedSymbol,
  favorites,
  search,
  onSearchChange,
  onSelect,
  onToggleFavorite,
}: Props) {
  const query = search.trim().toLowerCase();
  const filtered = pairs.filter((pair) => {
    if (!query) return true;
    return (
      pair.symbol.includes(query) ||
      pair.displayName.toLowerCase().includes(query) ||
      pair.baseCurrency.includes(query)
    );
  });

  const favoritePairs = filtered.filter((p) => favorites.includes(p.symbol));
  const restPairs = filtered.filter((p) => !favorites.includes(p.symbol));

  return (
    <section className="pair-selector" aria-labelledby="pair-selector-title">
      <h2 id="pair-selector-title">Trading pair</h2>
      <label className="pair-search">
        <span className="visually-hidden">Search pairs</span>
        <input
          type="search"
          placeholder="Search USDT pairs"
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
          data-testid="pair-search"
        />
      </label>

      {favoritePairs.length > 0 ? (
        <div className="pair-group" data-testid="favorites-list">
          <h3>Favorites</h3>
          <ul>
            {favoritePairs.map((pair) => (
              <PairRow
                key={pair.symbol}
                pair={pair}
                selected={pair.symbol === selectedSymbol}
                favorited
                onSelect={onSelect}
                onToggleFavorite={onToggleFavorite}
              />
            ))}
          </ul>
        </div>
      ) : null}

      <div className="pair-group" data-testid="all-pairs-list">
        <h3>All USDT pairs</h3>
        {restPairs.length === 0 && favoritePairs.length === 0 ? (
          <p>No matching pairs.</p>
        ) : (
          <ul>
            {restPairs.map((pair) => (
              <PairRow
                key={pair.symbol}
                pair={pair}
                selected={pair.symbol === selectedSymbol}
                favorited={favorites.includes(pair.symbol)}
                onSelect={onSelect}
                onToggleFavorite={onToggleFavorite}
              />
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}

function PairRow({
  pair,
  selected,
  favorited,
  onSelect,
  onToggleFavorite,
}: {
  pair: TradingPair;
  selected: boolean;
  favorited: boolean;
  onSelect: (symbol: string) => void;
  onToggleFavorite: (symbol: string) => void;
}) {
  return (
    <li className={selected ? "pair-row pair-row--selected" : "pair-row"}>
      <button
        type="button"
        className="pair-row__select"
        onClick={() => onSelect(pair.symbol)}
        aria-pressed={selected}
      >
        {pair.displayName}
        <span className="pair-row__symbol">{pair.symbol}</span>
      </button>
      <button
        type="button"
        className="pair-row__fav"
        aria-label={favorited ? `Unfavorite ${pair.displayName}` : `Favorite ${pair.displayName}`}
        onClick={() => onToggleFavorite(pair.symbol)}
      >
        {favorited ? "★" : "☆"}
      </button>
    </li>
  );
}
