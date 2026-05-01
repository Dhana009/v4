/* global React, Icons */
// AutoWorkbench — small reusable bits used across the panel.

const { Icons: I } = window;

function Badge({ kind, children }) {
  return <span className={`aw-badge b-${kind}`}>{children}</span>;
}

function ActionTag({ kind }) {
  const labels = { click: "click", fill: "fill", assert: "assert", nav: "navigate", navigate: "navigate" };
  const cls = kind === "navigate" ? "nav" : kind;
  return <span className={`aw-actag a-${cls}`}>{labels[kind] || kind}</span>;
}

function Card({ tone, title, titleIcon, link, linkIcon, onLink, children, dense, style }) {
  return (
    <div className={`aw-card${tone ? " " + tone : ""}`} style={style}>
      {title && (
        <div className="aw-card-hd">
          <div className={`aw-card-title${tone ? " t-" + tone : ""}`}>
            {titleIcon}
            {title}
          </div>
          <div className="aw-card-spacer" />
          {link && (
            <a className="aw-card-link" onClick={onLink}>
              {link}
              {linkIcon || <I.Caret size={11} />}
            </a>
          )}
        </div>
      )}
      <div className={`aw-card-body${dense ? " dense" : ""}`}>{children}</div>
    </div>
  );
}

function ElementSnap({ tag, text, locator }) {
  return (
    <div className="aw-elem-snap">
      <div className="ic">{tag || "el"}</div>
      <div className="info">
        <div className="t">{text}</div>
        <div className="l">{locator}</div>
      </div>
    </div>
  );
}

// Tiny syntax-highlight for the locator/code chips
function Mono({ children, tight, className = "" }) {
  return <div className={`aw-mono${tight ? " tight" : ""} ${className}`}>{children}</div>;
}

function CodeLine({ tokens }) {
  return (
    <>
      {tokens.map((t, i) => {
        if (typeof t === "string") return <span key={i}>{t}</span>;
        return <span key={i} className={`tk-${t[0]}`}>{t[1]}</span>;
      })}
    </>
  );
}

function IconBtn({ icon, title, onClick }) {
  return (
    <button className="aw-iconbtn" title={title} onClick={onClick}>
      {icon}
    </button>
  );
}

window.AW = { Badge, ActionTag, Card, ElementSnap, Mono, CodeLine, IconBtn };
