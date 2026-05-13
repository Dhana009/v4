// components/code/CodeExport.jsx — Export/copy backend code only
// S7-0810: disabled unless codePreview exists.
import React from "react";

export function CodeExport({ codePreview, onCopy, onExport }) {
  const hasCode = !!codePreview;
  const text =
    typeof codePreview === "string"
      ? codePreview
      : codePreview && (codePreview.code ?? codePreview.content)
      ? codePreview.code ?? codePreview.content
      : "";

  return (
    <div data-testid="code-export" className="aw-code-export">
      <button
        type="button"
        data-testid="code-copy"
        disabled={!hasCode}
        onClick={() =>
          typeof onCopy === "function" && onCopy({ type: "copy_code", code: text })
        }
      >
        Copy code
      </button>
      <button
        type="button"
        data-testid="code-export-btn"
        disabled={!hasCode}
        onClick={() =>
          typeof onExport === "function" && onExport({ type: "export_code", code: text })
        }
      >
        Export
      </button>
    </div>
  );
}

export default CodeExport;
