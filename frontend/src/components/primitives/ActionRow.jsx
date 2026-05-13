import React from "react";

export function ActionRow({
  children,
  align = "start",
  "data-testid": testId = "aw-action-row",
}) {
  const justifyMap = {
    start: "flex-start",
    end: "flex-end",
    center: "center",
    between: "space-between",
  };

  return (
    <div
      data-testid={testId}
      style={{
        display: "flex",
        alignItems: "center",
        gap: "var(--aw-space-2)",
        justifyContent: justifyMap[align] ?? "flex-start",
      }}
    >
      {children}
    </div>
  );
}

export default ActionRow;
