import type { Experiment, GenerationSnapshot } from "./evolutionApi";

type Props = {
  experiment: Experiment | null;
};

function FitnessChart({ generations }: { generations: GenerationSnapshot[] }) {
  if (!generations.length) return null;
  const w = 320;
  const h = 120;
  const pad = 8;
  const xs = generations.map((g) => g.generation);
  const maxX = Math.max(...xs, 1);
  const vals = generations.flatMap((g) =>
    [g.fitnessMax, g.fitnessAvg].filter((v): v is number => typeof v === "number"),
  );
  const minY = vals.length ? Math.min(...vals) : 0;
  const maxY = vals.length ? Math.max(...vals) : 1;
  const span = maxY - minY || 1;

  function pt(gen: number, val: number) {
    const x = pad + (gen / maxX) * (w - 2 * pad);
    const y = h - pad - ((val - minY) / span) * (h - 2 * pad);
    return `${x},${y}`;
  }

  const maxLine = generations
    .filter((g) => typeof g.fitnessMax === "number")
    .map((g) => pt(g.generation, g.fitnessMax as number))
    .join(" ");
  const avgLine = generations
    .filter((g) => typeof g.fitnessAvg === "number")
    .map((g) => pt(g.generation, g.fitnessAvg as number))
    .join(" ");

  return (
    <svg
      width={w}
      height={h}
      role="img"
      aria-label="Fitness over generations"
      data-testid="evolution-fitness-chart"
    >
      <rect width={w} height={h} fill="transparent" stroke="currentColor" opacity={0.2} />
      {maxLine ? (
        <polyline fill="none" stroke="currentColor" strokeWidth={2} points={maxLine} />
      ) : null}
      {avgLine ? (
        <polyline
          fill="none"
          stroke="currentColor"
          strokeWidth={1}
          strokeDasharray="4 3"
          points={avgLine}
          opacity={0.7}
        />
      ) : null}
    </svg>
  );
}

export function ExperimentProgress({ experiment }: Props) {
  if (!experiment) {
    return <p className="auto-trading-lede">No experiment running.</p>;
  }
  const gens = experiment.generations ?? [];
  return (
    <div data-testid="evolution-progress">
      <p>
        Status: <strong data-testid="evolution-status">{experiment.status}</strong>
        {experiment.terminationReason ? ` (${experiment.terminationReason})` : ""}
      </p>
      {experiment.errorMessage ? (
        <p className="form-error" role="alert">
          {experiment.errorMessage}
        </p>
      ) : null}
      <FitnessChart generations={gens} />
      <div className="table-wrap">
        <table data-testid="evolution-generations-table">
          <thead>
            <tr>
              <th>Gen</th>
              <th>Best fitness</th>
              <th>Mean fitness</th>
              <th>Best phenotype</th>
            </tr>
          </thead>
          <tbody>
            {gens.map((g) => (
              <tr key={g.generation}>
                <td>{g.generation}</td>
                <td>{g.fitnessMax ?? "—"}</td>
                <td>{g.fitnessAvg ?? "—"}</td>
                <td>
                  <code>{g.bestPhenotype ?? "—"}</code>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {experiment.bestPhenotype ? (
        <p data-testid="evolution-best-phenotype">
          Best phenotype: <code>{experiment.bestPhenotype}</code>
          {experiment.trainFitness != null ? ` (train ${experiment.trainFitness})` : ""}
          {experiment.validationFitness != null
            ? ` · val ${experiment.validationFitness}`
            : ""}
        </p>
      ) : null}
    </div>
  );
}
