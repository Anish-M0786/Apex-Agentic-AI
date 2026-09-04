import {
  Download,
  ExternalLink,
  File,
  FileSpreadsheet,
  FileText,
  Presentation,
  CheckCircle2,
} from 'lucide-react';
import type { Artifact } from '@/types/artifact';

function fileTypeIcon(type: string) {
  const t = type.toLowerCase();
  if (t === 'xlsx' || t === 'excel' || t.includes('spreadsheet')) return FileSpreadsheet;
  if (t === 'pptx' || t === 'ppt' || t.includes('presentation')) return Presentation;
  if (t === 'pdf' || t === 'docx' || t === 'doc' || t.includes('word')) return FileText;
  return File;
}

function typeLabel(type: string): string {
  const t = type.toLowerCase();
  if (t === 'xlsx' || t === 'excel') return 'Excel Spreadsheet';
  if (t === 'pptx' || t === 'ppt') return 'PowerPoint';
  if (t === 'pdf') return 'PDF Document';
  if (t === 'docx' || t === 'doc') return 'Word Document';
  return type.toUpperCase();
}

function cleanFilename(filename: string): string {
  // Remove the "agent-result." prefix if present
  return filename.replace(/^agent-result\./, '').replace(/\.[^.]+$/, (ext) => ext);
}

export function ArtifactCard({ artifact }: { artifact: Artifact }) {
  const Icon = fileTypeIcon(artifact.type);
  const label = artifact.label || cleanFilename(artifact.filename);
  const typeName = typeLabel(artifact.type);

  return (
    <article className="apex-artifact" aria-label={`Generated file: ${label}`}>
      <div className="apex-artifact__icon-wrap" aria-hidden="true">
        <Icon size={22} />
      </div>

      <div className="apex-artifact__info">
        <strong className="apex-artifact__name">{label}</strong>
        <div className="apex-artifact__meta-row">
          <span className="apex-artifact__type">{typeName}</span>
          <span className="apex-artifact__sep" aria-hidden="true">·</span>
          <span className="apex-artifact__verified">
            <CheckCircle2 size={11} aria-hidden="true" />
            Verified
          </span>
        </div>
      </div>

      <div className="apex-artifact__actions">
        <a
          href={artifact.url}
          target="_blank"
          rel="noreferrer"
          className="apex-artifact__btn apex-artifact__btn--open"
          aria-label={`Open ${label}`}
        >
          <ExternalLink size={14} aria-hidden="true" />
          Open
        </a>
        <a
          href={artifact.url}
          download
          className="apex-artifact__btn apex-artifact__btn--download"
          aria-label={`Download ${label}`}
        >
          <Download size={14} aria-hidden="true" />
          Download
        </a>
      </div>
    </article>
  );
}
