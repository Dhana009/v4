/* global React */
// AutoWorkbench — small SVG icon set used across the panel.

const Icons = {};

const mk = (path, viewBox = "0 0 16 16", strokeWidth = 1.7) => ({ size = 16, ...rest } = {}) => (
  <svg width={size} height={size} viewBox={viewBox} fill="none" stroke="currentColor"
       strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" {...rest}>
    {path}
  </svg>
);

Icons.Play = mk(<path d="M4 3l9 5-9 5z" fill="currentColor" stroke="none"/>);
Icons.Pause = mk(<><rect x="4" y="3" width="3" height="10" fill="currentColor" stroke="none"/><rect x="9" y="3" width="3" height="10" fill="currentColor" stroke="none"/></>);
Icons.Plus = mk(<><path d="M8 3v10M3 8h10"/></>);
Icons.Trash = mk(<><path d="M3 4.5h10M6 4.5v-1a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v1M4.5 4.5v8a1 1 0 0 0 1 1h5a1 1 0 0 0 1-1v-8M7 7v4M9 7v4"/></>);
Icons.Edit = mk(<><path d="M11 2.5l2.5 2.5L6 12.5l-3 .5.5-3z"/></>);
Icons.Pin = mk(<><path d="M9.5 2.5l4 4-2 1-1.5 4-1.5-1.5-3 3-.5-.5 3-3L6.5 8 10.5 6.5z" fill="currentColor" stroke="none"/></>);
Icons.Check = mk(<><path d="M3 8.5L6.5 12 13 4"/></>, "0 0 16 16", 2);
Icons.X = mk(<><path d="M4 4l8 8M12 4l-8 8"/></>, "0 0 16 16", 2);
Icons.Settings = mk(<><circle cx="8" cy="8" r="2"/><path d="M8 1v2M8 13v2M3.5 3.5l1.5 1.5M11 11l1.5 1.5M1 8h2M13 8h2M3.5 12.5L5 11M11 5l1.5-1.5"/></>);
Icons.Collapse = mk(<><path d="M9 3l-4 5 4 5"/></>, "0 0 16 16", 1.7);
Icons.Copy = mk(<><rect x="5" y="5" width="8" height="8" rx="1.5"/><path d="M3 11V4a1 1 0 0 1 1-1h7"/></>);
Icons.More = mk(<><circle cx="3.5" cy="8" r="1" fill="currentColor" stroke="none"/><circle cx="8" cy="8" r="1" fill="currentColor" stroke="none"/><circle cx="12.5" cy="8" r="1" fill="currentColor" stroke="none"/></>);
Icons.Replay = mk(<><path d="M3 8a5 5 0 1 1 1.5 3.5"/><path d="M3 4v3.5h3.5"/></>);
Icons.Send = mk(<><path d="M2 8L14 2 11 14 8 9z"/></>);
Icons.Wand = mk(<><path d="M11 2l1.5 1.5M14 5l-1.5-1.5M3 13l8-8M2 7l1 1M9 14l1-1M13 11l1 1"/></>);
Icons.Warn = mk(<><path d="M8 2L1.5 13h13z"/><path d="M8 6.5v3M8 11v.5"/></>, "0 0 16 16", 1.5);
Icons.Bolt = mk(<><path d="M9 1L3 9h4l-1 6 6-8H8z" fill="currentColor" stroke="none"/></>);
Icons.Camera = mk(<><rect x="2" y="4.5" width="12" height="9" rx="1.5"/><circle cx="8" cy="9" r="2.5"/><path d="M5.5 4.5l1-1.5h3l1 1.5"/></>);
Icons.Globe = mk(<><circle cx="8" cy="8" r="6"/><path d="M2 8h12M8 2c2 2 2 10 0 12M8 2c-2 2-2 10 0 12"/></>);
Icons.Mouse = mk(<><path d="M3 3l4 11 1.5-4 4-1.5z" fill="currentColor" stroke="none"/></>);
Icons.Spark = mk(<><path d="M8 1v4M8 11v4M1 8h4M11 8h4M3.2 3.2l2.8 2.8M10 10l2.8 2.8M3.2 12.8L6 10M10 6l2.8-2.8"/></>);
Icons.Lock = mk(<><rect x="3" y="7" width="10" height="6.5" rx="1.2"/><path d="M5 7V5a3 3 0 0 1 6 0v2"/></>);
Icons.Code = mk(<><path d="M5 4L1 8l4 4M11 4l4 4-4 4M9 3l-2 10"/></>);
Icons.Beaker = mk(<><path d="M6 2v4l-3 6.5a1 1 0 0 0 1 1.5h8a1 1 0 0 0 1-1.5L10 6V2M5 2h6"/></>);
Icons.List = mk(<><path d="M5 4h9M5 8h9M5 12h9M2 4h.01M2 8h.01M2 12h.01"/></>, "0 0 16 16", 1.7);
Icons.Search = mk(<><circle cx="7" cy="7" r="4.5"/><path d="M10.5 10.5L13.5 13.5"/></>);
Icons.Layers = mk(<><path d="M8 2l6 3-6 3-6-3z"/><path d="M2 8l6 3 6-3M2 11l6 3 6-3"/></>);
Icons.Eye = mk(<><path d="M1 8s2.5-4.5 7-4.5S15 8 15 8s-2.5 4.5-7 4.5S1 8 1 8z"/><circle cx="8" cy="8" r="2"/></>);
Icons.Caret = mk(<><path d="M3 6l5 4 5-4"/></>, "0 0 16 16", 1.7);
Icons.Sparkles = mk(<><path d="M5 1l1 3 3 1-3 1-1 3-1-3-3-1 3-1zM12 8l.7 2 2 .7-2 .7-.7 2-.7-2-2-.7 2-.7z" fill="currentColor" stroke="none"/></>);
Icons.Paperclip = mk(<><path d="M11 4l-5.5 5.5a2.5 2.5 0 0 0 3.5 3.5L14 7.5a4 4 0 0 0-5.5-5.5L3 7.5"/></>);

window.Icons = Icons;
