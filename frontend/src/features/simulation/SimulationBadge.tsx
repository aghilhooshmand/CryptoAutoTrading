interface Props {
  label?: "SIMULATION" | "REAL";
}

export function SimulationBadge({ label = "SIMULATION" }: Props) {
  const isReal = label === "REAL";
  return (
    <span
      className={isReal ? "simulation-badge real-badge" : "simulation-badge"}
      data-testid={isReal ? "real-badge" : "simulation-badge"}
      role="status"
    >
      {label}
    </span>
  );
}
