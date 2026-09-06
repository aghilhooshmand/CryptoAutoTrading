/** Evolution / UGE lab API client (Feature 020). */

export type ExperimentConfigBody = {
  symbol: string;
  timeframe: string;
  startTime: string;
  endTime: string;
  populationSize: number;
  nGenerations: number;
  seed: number;
  fitnessId: string;
  trainRatio: number;
  valRatio: number;
  testRatio: number;
  startingCapital?: string;
  feeRate?: string;
  slippageRate?: string;
  leaves?: string[];
  compositionOps?: string[];
  paramAlternatives?: Record<string, number[]>;
};

export type GenerationSnapshot = {
  generation: number;
  fitnessMax?: number | null;
  fitnessAvg?: number | null;
  fitnessMin?: number | null;
  bestPhenotype?: string | null;
  recordedAt?: string;
};

export type Experiment = {
  id: string;
  status: string;
  bestPhenotype?: string | null;
  trainFitness?: number | null;
  validationFitness?: number | null;
  fitnessId?: string;
  generationCount?: number;
  errorMessage?: string | null;
  terminationReason?: string | null;
  generations?: GenerationSnapshot[];
  config?: Record<string, unknown>;
};

async function parseError(res: Response): Promise<string> {
  try {
    const data = await res.json();
    const detail = data?.detail;
    if (detail && typeof detail === "object" && detail.message) return String(detail.message);
    if (typeof detail === "string") return detail;
    return res.statusText;
  } catch {
    return res.statusText;
  }
}

export async function listExperiments(): Promise<Experiment[]> {
  const res = await fetch("/uge/experiments");
  if (!res.ok) throw new Error(await parseError(res));
  const data = (await res.json()) as { experiments?: Experiment[] };
  return data.experiments ?? [];
}

export async function createExperiment(body: ExperimentConfigBody): Promise<Experiment> {
  const res = await fetch("/uge/experiments", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function getExperiment(id: string): Promise<Experiment> {
  const res = await fetch(`/uge/experiments/${encodeURIComponent(id)}`);
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function cancelExperiment(id: string): Promise<Experiment> {
  const res = await fetch(`/uge/experiments/${encodeURIComponent(id)}/cancel`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function freezeExperiment(
  id: string,
  displayName: string,
): Promise<{ strategyId: string; displayName: string }> {
  const res = await fetch(`/uge/experiments/${encodeURIComponent(id)}/freeze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ displayName }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}
