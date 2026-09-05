/** Client for Feature 019 frozen UGE artifacts. */

export interface FrozenArtifact {
  id?: string;
  phenotype: string;
  trainFitness?: number | null;
  validationFitness?: number | null;
  fitnessId?: string;
  seed?: number;
  createdAt?: string;
  path?: string;
}

export async function listFrozenArtifacts(): Promise<FrozenArtifact[]> {
  const res = await fetch("/uge/frozen");
  if (!res.ok) {
    throw new Error(`Failed to list frozen phenotypes (${res.status})`);
  }
  const data = (await res.json()) as { artifacts?: FrozenArtifact[] };
  return data.artifacts ?? [];
}
