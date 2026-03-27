import { DataTable } from "../components/DataTable";
import type { DashboardSnapshot } from "../types/dashboard";

type ModelsProps = {
  snapshot: DashboardSnapshot | null;
};

export function Models({ snapshot }: ModelsProps) {
  return (
    <section className="panel page-panel">
      <div className="panel-header">
        <h3>Models</h3>
        <p>Current baseline registry used to drive research signals and simulated execution.</p>
      </div>
      <DataTable
        columns={["ID", "Name", "Type", "Status", "F1", "ROC-AUC"]}
        rows={(snapshot?.models ?? []).map((model) => [
          model.id,
          model.name,
          model.model_type,
          model.status,
          model.f1.toFixed(3),
          model.roc_auc.toFixed(3),
        ])}
      />
    </section>
  );
}
