import type { Experiment, GenerationSnapshot } from "./evolutionApi";

type Props = {
  experiment: Experiment | null;
};

function FitnessChart({ generations }: { generations: GenerationSnapshot[] }) {
  if (!generations.length) return null;
  const w = 480;
  const h = 140;
  const pad = 10;
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
    <div className="evolution-chart-wrap">
      <svg
        viewBox={`0 0 ${w} ${h}`}
        role="img"
        aria-label="Fitness over generations"
        data-testid="evolution-fitness-chart"
        className="evolution-fitness-chart"
      >
        <rect
          width={w}
          height={h}
          fill="transparent"
          stroke="var(--line)"
          strokeWidth={1}
        />
        {maxLine ? (
          <polyline
            fill="none"
            stroke="var(--accent)"
            strokeWidth={2}
            points={maxLine}
          />
        ) : null}
        {avgLine ? (
          <polyline
            fill="none"
            stroke="var(--muted)"
            strokeWidth={1.5}
            strokeDasharray="4 3"
            points={avgLine}
          />
        ) : null}
      </svg>
      <p className="field-hint">Solid = best fitness · Dashed = mean fitness</p>
    </div>
  );
}

export function ExperimentProgress({ experiment }: Props) {
  if (!experiment) {
    return (
      <section
        className="backtest-results"
        data-testid="evolution-progress"
        aria-labelledby="evolution-progress-title"
      >
        <h3 id="evolution-progress-title">Experiment progress</h3>
        <p className="note">No experiment running.</p>
      </section>
    );
  }

  const gens = experiment.generations ?? [];

  return (
    <section
      className="backtest-results"
      data-testid="evolution-progress"
      aria-labelledby="evolution-progress-title"
    >
      <h3 id="evolution-progress-title">Experiment progress</h3>
      <dl className="sim-dl">
        <div>
          <dt>Status</dt>
          <dd data-testid="evolution-status">
            {experiment.status}
            {experiment.terminationReason ? ` (${experiment.terminationReason})` : ""}
          </dd>
        </div>
        {experiment.bestPhenotype ? (
          <div>
            <dt>Best phenotype</dt>
            <dd data-testid="evolution-best-phenotype">
              <code>{experiment.bestPhenotype}</code>
              {experiment.trainFitness != null ? ` · train ${experiment.trainFitness}` : ""}
              {experiment.validationFitness != null
                ? ` · val ${experiment.validationFitness}`
                : ""}
            </dd>
          </div>
        ) : null}
        {experiment.generationCount != null ? (
          <div>
            <dt>Generations recorded</dt>
            <dd>{experiment.generationCount}</dd>
          </div>
        ) : null}
      </dl>

      {experiment.errorMessage ? (
        <p className="form-error" role="alert">
          {experiment.errorMessage}
        </p>
      ) : null}

      <FitnessChart generations={gens} />

      <div className="table-wrap">
        <table data-testid="evolution-generations-table" className="comparison-table">
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
    </section>
  );
}
