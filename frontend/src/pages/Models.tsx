import { DataTable } from "../components/DataTable";
import { PageIntro } from "../components/page/PageIntro";
import type { DashboardSnapshot } from "../types/dashboard";

type ModelsProps = {
  snapshot: DashboardSnapshot | null;
};

export function Models({ snapshot }: ModelsProps) {
  const models = snapshot?.models ?? [];
  const averageF1 = models.length > 0 ? models.reduce((total, model) => total + model.f1, 0) / models.length : 0;
  const averageRocAuc = models.length > 0 ? models.reduce((total, model) => total + model.roc_auc, 0) / models.length : 0;
  const readyModels = models.filter((model) => /(ready|active|deployed|production)/i.test(model.status)).length;
  const leadModel = [...models].sort((left, right) => right.f1 + right.roc_auc - (left.f1 + left.roc_auc))[0] ?? null;

  return (
    <div className="dashboard-page">
      <PageIntro
        eyebrow="Model Registry"
        title="Research model lineup"
        description="Compare baseline quality, deployment readiness, and the strongest candidates before promoting forecasts into the signal tape."
        stats={[
          {
            label: "Tracked models",
            value: models.length,
            note: `${readyModels}/${models.length || 0} in ready or active state`,
            tone: "accent",
          },
          {
            label: "Average F1",
            value: averageF1.toFixed(3),
            note: "Mean classification balance across the current registry",
            tone: averageF1 >= 0.6 ? "positive" : "neutral",
          },
          {
            label: "Average ROC-AUC",
            value: averageRocAuc.toFixed(3),
            note: "Mean ranking quality across stored experiments",
            tone: averageRocAuc >= 0.7 ? "positive" : "neutral",
          },
          {
            label: "Lead model",
            value: leadModel?.name ?? "-",
            note: leadModel ? `${leadModel.model_type} • F1 ${leadModel.f1.toFixed(3)}` : "No model metrics available",
            tone: "accent",
          },
        ]}
      />

      {models.length > 0 ? (
        <section className="detail-card-grid">
          {[...models]
            .sort((left, right) => right.f1 + right.roc_auc - (left.f1 + left.roc_auc))
            .slice(0, 3)
            .map((model) => (
              <article className="detail-card" key={model.id}>
                <div className="detail-card-topline">
                  <span className="metric-label">Model candidate</span>
                  <span className={`tone-pill ${getModelTone(model.status)}`}>{model.status}</span>
                </div>
                <strong>{model.name}</strong>
                <p>{model.model_type} baseline currently registered for research signal generation and evaluation.</p>
                <div className="detail-card-meta">
                  <span>F1 {model.f1.toFixed(3)}</span>
                  <span>ROC-AUC {model.roc_auc.toFixed(3)}</span>
                </div>
              </article>
            ))}
        </section>
      ) : null}

      <section className="panel page-panel">
        <div className="panel-header">
          <div>
            <h3>Models</h3>
            <p>Current baseline registry used to drive research signals and simulated execution.</p>
          </div>
        </div>
        <DataTable
          columns={["ID", "Name", "Type", "Status", "F1", "ROC-AUC"]}
          rows={models.map((model) => [
            model.id,
            <span className="table-symbol" key={`model-name-${model.id}`}>
              {model.name}
            </span>,
            model.model_type,
            <span className={`tone-pill ${getModelTone(model.status)}`} key={`model-status-${model.id}`}>
              {model.status}
            </span>,
            <span className="table-number" key={`model-f1-${model.id}`}>
              {model.f1.toFixed(3)}
            </span>,
            <span className="table-number" key={`model-roc-${model.id}`}>
              {model.roc_auc.toFixed(3)}
            </span>,
          ])}
          caption="Baseline and champion registry"
          footnote="Evaluation metrics summarize past research runs only and must not be treated as guarantees of future market performance."
        />
      </section>
    </div>
  );
}

function getModelTone(status: string) {
  const normalizedStatus = status.toLowerCase();
  if (normalizedStatus.includes("active") || normalizedStatus.includes("ready") || normalizedStatus.includes("deployed")) {
    return "tone-positive";
  }
  if (normalizedStatus.includes("train") || normalizedStatus.includes("fit") || normalizedStatus.includes("queue")) {
    return "tone-warning";
  }
  if (normalizedStatus.includes("error") || normalizedStatus.includes("fail")) {
    return "tone-negative";
  }
  return "tone-accent";
}
